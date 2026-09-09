# Elderly Wellbeing Monitor

## Project purpose

The Elderly Wellbeing Monitor is a caregiver support web application that uses a laptop webcam, OpenCV face detection, and a pretrained Hugging Face facial-expression classifier. It reports observable facial-expression predictions, confidence scores, and caregiver attention indicators.

It is not a medical diagnostic system and does not claim to identify a person's true internal emotional state.

## Completed application flow

- Caregiver registration and login with JWT authentication
- Protected dashboard, profile, live monitoring, history, analytics, reports, and settings routes
- Elderly profile management
- Monitoring session start and stop
- Laptop webcam access through the browser
- OpenCV face detection and face cropping
- Real Hugging Face model inference with `AI_DEMO_MODE=false`
- Five-frame temporal probability smoothing per session
- Stabilized observation saving without continuous video storage
- History and analytics based on stored observations
- Privacy and consent acknowledgement before starting monitoring
- API documentation through FastAPI `/docs`

## Technology areas

1. Artificial intelligence and machine learning: facial-expression classification and offline FER-2013 experiments.
2. Computer vision: webcam capture, OpenCV face detection, face cropping, and frame processing.
3. Cloud computing: deployment and managed database architecture are documented as future extensions; no cloud service is claimed as complete.
4. Mobile application technology: a mobile/PWA extension is documented as future work; no mobile implementation is claimed as complete.

## Scope limitations

The system stores derived observations only. It does not continuously store webcam frames, provide clinical conclusions, or replace caregiver judgement. See [ai_ml_implementation.md](ai_ml_implementation.md) for model and evaluation limitations.
