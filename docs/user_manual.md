# User Manual

## Start the application

From `D:\elderly-wellbeing-monitor`:

```powershell
.\START_ALL.ps1
```

The application opens at `http://127.0.0.1:5173`. The API documentation is at `http://127.0.0.1:8000/docs`.

The launcher uses the existing root `.venv`; it does not create a new environment. Ensure Node dependencies exist under `frontend/node_modules`.

## Caregiver workflow

1. Sign in or create a caregiver account.
2. Review the Dashboard and open Profiles to add a monitored person.
3. Open Live Monitoring.
4. Select a profile and acknowledge the consent/privacy notice.
5. Start a monitoring session, then start the webcam.
6. Position one face clearly in front of the camera.
7. Review face status, real model status, raw prediction, smoothed expression, and confidence.
8. Save only a stabilized meaningful observation.
9. Stop the webcam and session.
10. Use History for saved records and Analytics for distribution, trends, and attention indicators.

## Privacy and interpretation

Continuous webcam video is not stored. Saved records contain derived expression, confidence, timestamp, session, profile, and attention indicator values. These are observable facial-expression predictions only, not medical diagnoses or proof of internal emotional state.

## Troubleshooting

- If the frontend does not load, confirm port 5173 is available and run `npm.cmd install` in `frontend`.
- If the API does not load, confirm port 8000 is available and that the existing `.venv` contains backend dependencies.
- If no face is detected, improve lighting and position the face fully inside the camera view.
- If the model is unavailable, confirm `AI_DEMO_MODE=false`, internet access for the first model download, and the backend terminal error. The UI will not fabricate a prediction.
