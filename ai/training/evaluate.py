from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.training.dataset import FER_LABELS, create_dataloaders
from ai.training.train import build_model


def safe_divide(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def compute_class_metrics(cm: np.ndarray, labels: list[str]) -> dict[str, dict[str, float]]:
    per_class: dict[str, dict[str, float]] = {}
    for i, label in enumerate(labels):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2.0 * precision * recall, precision + recall)
        support = int(cm[i, :].sum())
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return per_class


def evaluate_model(
    model_path: str | Path,
    data_dir: str | Path,
    batch_size: int = 32,
    summary_path: str | Path | None = None,
    confusion_path: str | Path | None = None,
) -> dict:
    data_root = Path(data_dir)
    loaders = create_dataloaders(data_root, batch_size=batch_size, val_fraction=0.2, num_workers=0, seed=42)
    model = build_model(num_classes=len(FER_LABELS), pretrained=False)
    checkpoint = torch.load(str(model_path), map_location="cpu")

    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        model.load_state_dict(checkpoint["state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model.eval()
    all_labels: list[int] = []
    all_preds: list[int] = []
    start_time = time.perf_counter()

    with torch.no_grad():
        for images, labels in loaders["test_loader"]:
            logits = model(images)
            preds = logits.argmax(dim=1)
            all_labels.extend(labels.tolist())
            all_preds.extend(preds.tolist())

    y_true = np.asarray(all_labels, dtype=np.int64)
    y_pred = np.asarray(all_preds, dtype=np.int64)
    cm = np.zeros((len(FER_LABELS), len(FER_LABELS)), dtype=np.int64)
    for actual, pred in zip(y_true, y_pred):
        cm[actual, pred] += 1

    total = int(cm.sum())
    accuracy = safe_divide(float(np.trace(cm)), float(total))

    per_class = compute_class_metrics(cm, FER_LABELS)
    precision_values = [entry["precision"] for entry in per_class.values()]
    recall_values = [entry["recall"] for entry in per_class.values()]
    f1_values = [entry["f1"] for entry in per_class.values()]
    supports = [entry["support"] for entry in per_class.values()]

    macro_precision = float(np.mean(precision_values)) if precision_values else 0.0
    macro_recall = float(np.mean(recall_values)) if recall_values else 0.0
    macro_f1 = float(np.mean(f1_values)) if f1_values else 0.0

    weighted_precision = safe_divide(float(np.sum(np.asarray(precision_values) * np.asarray(supports))), float(sum(supports)))
    weighted_recall = safe_divide(float(np.sum(np.asarray(recall_values) * np.asarray(supports))), float(sum(supports)))
    weighted_f1 = safe_divide(float(np.sum(np.asarray(f1_values) * np.asarray(supports))), float(sum(supports)))

    eval_time = time.perf_counter() - start_time

    result = {
        "checkpoint": str(model_path),
        "dataset_root": str(data_root),
        "test_sample_count": total,
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_precision,
        "weighted_recall": weighted_recall,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "labels": FER_LABELS,
        "evaluation_time_seconds": eval_time,
    }

    out_dir = PROJECT_ROOT / "ai" / "models" / "trained"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = Path(summary_path) if summary_path is not None else out_dir / "fer2013_eval_metrics_epoch1.json"
    confusion_path = Path(confusion_path) if confusion_path is not None else out_dir / "fer2013_confusion_matrix_epoch1.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    confusion_path.parent.mkdir(parents=True, exist_ok=True)

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    with confusion_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["label", *FER_LABELS])
        for idx, label in enumerate(FER_LABELS):
            row = [label] + [int(v) for v in cm[idx]]
            writer.writerow(row)

    print(json.dumps({
        "checkpoint": str(model_path),
        "test_sample_count": total,
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "evaluation_time_seconds": eval_time,
        "summary_path": str(summary_path),
        "confusion_matrix_path": str(confusion_path),
    }, indent=2))

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a FER-2013 model checkpoint")
    parser.add_argument("--model-path", required=True, help="Path to model checkpoint")
    parser.add_argument("--data-dir", default=str(PROJECT_ROOT / "ai" / "datasets" / "fer2013"), help="Path to FER-2013 dataset root")
    parser.add_argument("--batch-size", type=int, default=32, help="Evaluation batch size")
    parser.add_argument("--summary-path", default=None, help="Optional path to save the summary JSON")
    parser.add_argument("--confusion-path", default=None, help="Optional path to save the confusion matrix CSV")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_model(args.model_path, args.data_dir, batch_size=args.batch_size, summary_path=args.summary_path, confusion_path=args.confusion_path)
