# FER-2013 training pipeline

This directory contains an isolated training pipeline for the FER-2013 dataset. It is separate from the production webcam application and does not replace the active pretrained model used by the live app.

## Dataset

Expected structure:

```text
ai/datasets/fer2013/
  train/
    angry/
    disgust/
    fear/
    happy/
    neutral/
    sad/
    surprise/
  test/
    angry/
    disgust/
    fear/
    happy/
    neutral/
    sad/
    surprise/
```

## Model

A lightweight CPU-friendly transfer-learning model is used:

- MobileNetV3 Small
- pretrained ImageNet weights when available
- replaced classifier head for 7 FER-2013 classes

## Sample usage

From the project root:

```powershell
D:\elderly-wellbeing-monitor\backend\.venv\Scripts\python.exe ai/training/train.py --smoke-test --data-dir ai/datasets/fer2013
```

This runs a short smoke test only.

## Notes

- The main production app remains unchanged.
- The training pipeline is intentionally independent.
- Class imbalance is handled with a weighted sampler during training.
- Validation is created from the training split when no dedicated val split exists.
