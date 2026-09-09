from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import torch
from torch import nn
from torchvision import models

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "ai" / "datasets" / "fer2013"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.training.dataset import FER_LABELS, create_dataloaders


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(num_classes: int = len(FER_LABELS), pretrained: bool = True) -> nn.Module:
    try:
        model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
        return model
    except Exception:
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
        print("[train] Pretrained weights not available; falling back to random initialization.")
        return model


def compute_class_weights_from_train_data(class_counts: dict[str, int]) -> torch.Tensor:
    ordered_counts = [class_counts.get(label, 0) for label in FER_LABELS]
    nonzero = [count for count in ordered_counts if count > 0]
    if not nonzero:
        return torch.ones(len(FER_LABELS), dtype=torch.float32)
    total = sum(nonzero)
    num_classes = len(FER_LABELS)
    weights = [total / (num_classes * count) if count > 0 else 1.0 for count in ordered_counts]
    return torch.tensor(weights, dtype=torch.float32)


def smoke_test(data_dir: str | Path, batch_size: int = 8, limit_batches: int = 2) -> None:
    loaders = create_dataloaders(data_dir=data_dir, batch_size=batch_size, val_fraction=0.2, num_workers=0, seed=42)
    train_loader = loaders["train_loader"]
    sample_images, sample_labels = next(iter(train_loader))

    print(f"dataset_detected: {Path(data_dir)}")
    print(f"class_counts: {loaders['class_counts']}")
    print(f"batch_shape: {tuple(sample_images.shape)}")
    print(f"label_shape: {tuple(sample_labels.shape)}")

    device = torch.device("cpu")
    model = build_model(num_classes=len(FER_LABELS), pretrained=False).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    for step, (images, labels) in enumerate(train_loader):
        if step >= limit_batches:
            break
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        print(f"smoke_step={step} loss={loss.item():.4f}")

    print("SMOKE_TEST_OK")


def train_one_epoch_weighted(
    data_dir: str | Path,
    epochs: int = 1,
    batch_size: int = 32,
    num_workers: int = 0,
    output_path: str | Path | None = None,
    seed: int = 42,
) -> dict[str, float | str]:
    set_seed(seed)
    loaders = create_dataloaders(data_dir=data_dir, batch_size=batch_size, val_fraction=0.2, num_workers=num_workers, seed=seed)
    model = build_model(num_classes=len(FER_LABELS), pretrained=True)
    class_weights = compute_class_weights_from_train_data(loaders["class_counts"])
    device = torch.device("cpu")
    model = model.to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, labels in loaders["train_loader"]:
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"epoch={epoch + 1} avg_loss={running_loss / max(1, len(loaders['train_loader'])):.4f}")

    default_output = PROJECT_ROOT / "ai" / "models" / "trained" / "fer2013_mobilenetv3_small_weighted_epoch1_cpu.pt"
    checkpoint_path = Path(output_path) if output_path is not None else default_output
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_name": "mobilenet_v3_small",
            "state_dict": model.state_dict(),
            "class_weights": class_weights.tolist(),
            "train_class_counts": {label: loaders["class_counts"].get(label, 0) for label in FER_LABELS},
            "epochs": epochs,
            "seed": seed,
        },
        checkpoint_path,
    )
    print(f"saved_checkpoint={checkpoint_path}")
    return {
        "checkpoint": str(checkpoint_path),
        "class_weights": {label: float(class_weights[idx].item()) for idx, label in enumerate(FER_LABELS)},
    }


def train_one_epoch(data_dir: str | Path, epochs: int = 1, batch_size: int = 32, num_workers: int = 0) -> None:
    loaders = create_dataloaders(data_dir=data_dir, batch_size=batch_size, val_fraction=0.2, num_workers=num_workers, seed=42)
    model = build_model(num_classes=len(FER_LABELS), pretrained=True)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for batch_idx, (images, labels) in enumerate(loaders["train_loader"]):
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"epoch={epoch + 1} avg_loss={running_loss / max(1, len(loaders['train_loader'])):.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FER-2013 training smoke tests")
    parser.add_argument("--data-dir", default=str(DATASET_ROOT), help="Path to FER-2013 dataset root")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for smoke test")
    parser.add_argument("--limit-batches", type=int, default=2, help="Number of training batches in smoke test")
    parser.add_argument("--epochs", type=int, default=1, help="Training epochs to run when not using smoke test")
    parser.add_argument("--smoke-test", action="store_true", help="Run a short training smoke test only")
    parser.add_argument("--output-path", default=str(PROJECT_ROOT / "ai" / "models" / "trained" / "fer2013_mobilenetv3_small_weighted_epoch1_cpu.pt"), help="Path to save the weighted loss checkpoint")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.smoke_test:
        smoke_test(args.data_dir, batch_size=args.batch_size, limit_batches=args.limit_batches)
    else:
        train_one_epoch_weighted(args.data_dir, epochs=args.epochs, batch_size=args.batch_size, output_path=args.output_path)
