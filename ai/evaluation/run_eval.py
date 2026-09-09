"""
AI evaluation framework — accuracy, precision, recall, F1, confusion matrix.

Usage:
  python -m ai.evaluation.run_eval --predictions ai/evaluation/sample_predictions.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

LABELS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]


def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[list[int]]:
    index = {l: i for i, l in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for t, p in zip(y_true, y_pred):
        if t in index and p in index:
            matrix[index[t]][index[p]] += 1
    return matrix


def per_class_scores(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels)
    scores = {}
    for i, label in enumerate(labels):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(len(labels))) - tp
        fn = sum(cm[i][c] for c in range(len(labels))) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        scores[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(cm[i]),
        }
    return scores


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true:
        return 0.0
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return correct / len(y_true)


def evaluate(y_true: list[str], y_pred: list[str]) -> dict:
    return {
        "accuracy": round(accuracy(y_true, y_pred), 4),
        "per_class": per_class_scores(y_true, y_pred, LABELS),
        "confusion_matrix": {
            "labels": LABELS,
            "matrix": confusion_matrix(y_true, y_pred, LABELS),
        },
        "note": "Evaluation of observable facial-expression classification only; not clinical validation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="FER evaluation harness")
    parser.add_argument(
        "--predictions",
        type=str,
        default=str(Path(__file__).with_name("sample_predictions.json")),
    )
    args = parser.parse_args()
    data = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    y_true = [r["true"] for r in data]
    y_pred = [r["pred"] for r in data]
    result = evaluate(y_true, y_pred)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
