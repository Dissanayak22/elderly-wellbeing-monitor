# AI model setup

## Production runtime

The production service uses the real Hugging Face Transformers model:

`dima806/facial_emotions_image_detection`

The application is configured with `AI_DEMO_MODE=false`. Do not replace this model with the bundled one-epoch MobileNet experiment without a separate validation and deployment decision.

Install the dependencies from the existing environment requirements:

```powershell
cd D:\elderly-wellbeing-monitor
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install -r ai\requirements.txt
```

The first real prediction may download model files from Hugging Face and cache them locally. Network access is required on that first uncached startup. The pipeline runs on CPU by default and can take longer on the first request.

Set the environment explicitly:

```dotenv
AI_DEMO_MODE=false
```

Restart the backend and confirm `/api/health` reports `ai_demo_mode: false`. The live page reports `Real model` only after a face is detected and a real prediction is returned.

## Runtime pipeline

OpenCV decodes the JPEG payload, detects the largest face with the bundled Haar cascade, and passes the RGB face crop to the Transformers image-classification pipeline. The service averages the last five probability vectors for each monitoring session. No continuous webcam frame is stored.

If no face is detected, the API reports that state. If the model cannot load or inference fails, the API reports `AI model unavailable` or `AI prediction unavailable`; it does not invent a prediction.

## FER-2013 research baseline

The MobileNetV3-Small code under `ai/training` is an offline research experiment using the existing FER-2013 dataset. Its checkpoints, metrics, and confusion matrices under `ai/models/trained` are preserved for the final report. It is not the production runtime model.

Run the lightweight evaluation harness with:

```powershell
cd ai
..\.venv\Scripts\python.exe -m evaluation.run_eval --predictions evaluation\sample_predictions.json
..\.venv\Scripts\python.exe -m pytest tests
```

## Ethics wording

Always present outputs as **observable facial expression** AI predictions with a **confidence score**, plus optional **caregiver attention indicators**. Confidence is not accuracy, diagnosis, or proof of internal emotional state.
