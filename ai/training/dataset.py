from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "ai" / "datasets" / "fer2013"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FER_LABELS = ["sad", "disgust", "angry", "neutral", "fear", "surprise", "happy"]
LABEL_TO_INDEX = {label: idx for idx, label in enumerate(FER_LABELS)}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def discover_classes(dataset_root: str | Path) -> List[str]:
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"Dataset root not found: {root}")

    classes = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not classes:
        raise ValueError(f"No class directories found under {root}")
    return classes


def iter_image_files(class_dir: Path) -> List[Path]:
    files = []
    for item in sorted(class_dir.iterdir()):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(item)
    return files


def collect_items_for_split(split_dir: Path, class_names: Optional[List[str]] = None) -> Dict[str, List[Path]]:
    if class_names is None:
        class_names = discover_classes(split_dir)

    items: Dict[str, List[Path]] = {}
    for class_name in class_names:
        class_dir = split_dir / class_name
        if class_dir.exists():
            items[class_name] = iter_image_files(class_dir)
        else:
            items[class_name] = []
    return items


def _split_train_validation(items: List[Tuple[Path, int]], val_fraction: float, seed: int) -> Tuple[List[Tuple[Path, int]], List[Tuple[Path, int]]]:
    if val_fraction <= 0 or len(items) < 2:
        return items, []

    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)

    val_size = max(1, int(round(len(shuffled) * val_fraction)))
    if val_size >= len(shuffled):
        val_size = max(1, len(shuffled) // 5)
    if val_size >= len(shuffled):
        val_size = len(shuffled) - 1

    val_items = shuffled[:val_size]
    train_items = shuffled[val_size:]
    return train_items, val_items


class FER2013Dataset(Dataset):
    def __init__(
        self,
        items: List[Tuple[Path, int]],
        transform: Optional[transforms.Compose] = None,
    ) -> None:
        self.items = items
        self.transform = transform
        self.class_counts = Counter(label for _, label in items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int):
        image_path, label = self.items[index]
        image = Image.open(image_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, torch.tensor(label, dtype=torch.long)


def build_transform(train: bool = False) -> transforms.Compose:
    ops = [
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((224, 224)),
    ]

    if train:
        ops.append(transforms.RandomHorizontalFlip(p=0.5))

    ops.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )
    return transforms.Compose(ops)


def make_weighted_sampler(dataset: FER2013Dataset) -> WeightedRandomSampler:
    counts = dataset.class_counts
    weights = [1.0 / counts[label] for _, label in dataset.items]
    return WeightedRandomSampler(weights=weights, num_samples=len(weights), replacement=True)


def load_dataset_items(data_dir: str | Path, val_fraction: float = 0.2, seed: int = 42) -> Tuple[List[Tuple[Path, int]], List[Tuple[Path, int]], List[Tuple[Path, int]], List[str], Dict[str, int]]:
    root = Path(data_dir)
    train_root = root / "train"
    if not train_root.exists():
        raise FileNotFoundError(f"Missing training split at {train_root}")

    class_names = discover_classes(train_root)
    train_items: List[Tuple[Path, int]] = []
    for class_name in class_names:
        class_dir = train_root / class_name
        for image_path in iter_image_files(class_dir):
            train_items.append((image_path, LABEL_TO_INDEX[class_name]))

    if (root / "val").exists():
        val_items = []
        for class_name in class_names:
            class_dir = root / "val" / class_name
            if class_dir.exists():
                for image_path in iter_image_files(class_dir):
                    val_items.append((image_path, LABEL_TO_INDEX[class_name]))
        val_items = sorted(val_items, key=lambda item: str(item[0]))
    else:
        train_items, val_items = _split_train_validation(train_items, val_fraction=val_fraction, seed=seed)

    test_items: List[Tuple[Path, int]] = []
    test_root = root / "test"
    if test_root.exists():
        for class_name in class_names:
            class_dir = test_root / class_name
            if class_dir.exists():
                for image_path in iter_image_files(class_dir):
                    test_items.append((image_path, LABEL_TO_INDEX[class_name]))
    test_items = sorted(test_items, key=lambda item: str(item[0]))

    class_counts = {class_name: len(iter_image_files(train_root / class_name)) for class_name in class_names}
    return train_items, val_items, test_items, class_names, class_counts


def create_dataloaders(
    data_dir: str | Path,
    batch_size: int = 32,
    val_fraction: float = 0.2,
    num_workers: int = 0,
    seed: int = 42,
):
    train_items, val_items, test_items, class_names, class_counts = load_dataset_items(
        data_dir=data_dir,
        val_fraction=val_fraction,
        seed=seed,
    )

    train_ds = FER2013Dataset(train_items, transform=build_transform(train=True))
    val_ds = FER2013Dataset(val_items, transform=build_transform(train=False))
    test_ds = FER2013Dataset(test_items, transform=build_transform(train=False))

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        sampler=make_weighted_sampler(train_ds),
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    return {
        "train_loader": train_loader,
        "val_loader": val_loader,
        "test_loader": test_loader,
        "class_names": class_names,
        "class_counts": class_counts,
        "n_classes": len(FER_LABELS),
    }
