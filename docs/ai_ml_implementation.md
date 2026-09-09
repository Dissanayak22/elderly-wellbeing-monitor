# AI and ML Implementation

## Production model

The production application uses the Hugging Face model `dima806/facial_emotions_image_detection` through the Transformers image-classification pipeline. The model is loaded on CPU when `AI_DEMO_MODE=false`; the application does not generate random or fabricated predictions.

Runtime labels are normalized to:

`angry`, `disgust`, `fear`, `happy`, `sad`, `surprise`, `neutral`

The first inference may take longer while model files are downloaded and cached by Hugging Face. Network access is required for the first uncached startup.

## Computer vision pipeline

1. Decode the browser JPEG payload.
2. Detect faces using OpenCV Haar cascade.
3. Select the largest detected face.
4. Convert the crop from OpenCV BGR to RGB.
5. Run the Hugging Face classifier.
6. Average probability vectors across the last five frames in the monitoring session.
7. Return raw and smoothed predictions, confidence, face status, and timestamp.

If no face is found, the response says so. If the real model is unavailable, the response is `AI prediction unavailable`; no fake result is substituted.

## FER-2013 research experiment

The repository also contains a separate MobileNetV3-Small training and evaluation experiment using `ai/datasets/fer2013`. Existing checkpoints and results are preserved under `ai/models/trained`.

Recorded initial results:

- Validation accuracy: 52.49%
- Test accuracy: 51.16%
- Macro precision: 48.21%
- Macro recall: 54.09%
- Macro F1: 45.92%
- Weighted F1: 51.53%

These results are a one-epoch research baseline. The MobileNet checkpoint is not silently presented as the production model because its preprocessing, label mapping, and deployment validation have not been established as equivalent to the Hugging Face runtime model.

## Limitations and responsible interpretation

FER-2013 is not a substitute for a representative webcam deployment dataset. Class imbalance, lighting, pose, occlusion, cultural variation, and camera quality can affect predictions. A confidence score is model confidence, not accuracy or clinical certainty. All UI and reports must use observable facial-expression wording and must not claim medical diagnosis or true emotional-state recognition.
