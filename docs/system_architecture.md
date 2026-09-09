# System Architecture

```text
Browser webcam and React UI
          |
          | JSON over HTTP
          v
FastAPI backend :8000
  auth | profiles | sessions | observations | analytics | reports
          |
          +--> SQLAlchemy and SQLite database
          |
          +--> OpenCV face detection
                    |
                    +--> Hugging Face image-classification pipeline
                         dima806/facial_emotions_image_detection
```

## Runtime flow

1. A caregiver authenticates and receives a JWT.
2. The frontend loads caregiver-owned elderly profiles.
3. A monitoring session is created for one profile.
4. The browser requests webcam permission and captures a JPEG frame approximately every 2.5 seconds.
5. The backend decodes the frame, detects the largest face, and sends the crop to the real Hugging Face model.
6. The service averages the last five probability vectors for that session.
7. Only a meaningful stabilized result can be saved as an observation.
8. History, dashboard summaries, and analytics read stored observations.
9. Stopping a session prevents further predictions or observation writes for that session.

## Security boundaries

- JWT-protected application routes
- Caregiver ownership checks for profiles, sessions, observations, and reports
- CORS configured from `CORS_ORIGINS`
- SQLite foreign-key enforcement enabled
- Production startup rejects known development secrets
- Base64 prediction payloads are size-limited
- Raw webcam frames are not persisted

Cloud deployment and mobile clients are planned extensions, not completed runtime components.
