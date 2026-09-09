# Final Project Checklist

## Completed features

- [x] Caregiver login, registration, JWT-protected routes, and logout
- [x] Dashboard and elderly profile management
- [x] Monitoring sessions with active/ended state
- [x] Laptop webcam access and OpenCV face detection
- [x] Real Hugging Face facial-expression model with `AI_DEMO_MODE=false`
- [x] Raw confidence and five-frame temporal smoothing
- [x] Meaningful stabilized observation saving
- [x] History and real-data analytics/trend views
- [x] Consent/privacy acknowledgement and non-diagnostic wording
- [x] Ownership validation for profiles, sessions, observations, and reports
- [x] Preserved FER-2013 dataset, MobileNet experiment, checkpoints, and metrics
- [x] Cloud and mobile architecture documented honestly as future extensions

## Tested features

- [x] Backend automated tests: 9 passed
- [x] Frontend automated tests: 2 passed
- [x] Frontend production build
- [x] Backend `/api/health`
- [x] Frontend `http://127.0.0.1:5173`
- [x] Backend `http://127.0.0.1:8000/docs`
- [x] Session/profile ownership and stopped-session rejection

## Known limitations

- [ ] No automated browser test for webcam permission and full UI workflow
- [ ] Real model first startup requires Hugging Face download/cache
- [ ] FER-2013 MobileNet is a one-epoch research baseline, not the production runtime model
- [ ] Cloud deployment and mobile application are planned extensions, not complete implementations
- [ ] SQLite uses runtime table creation; a full migration tool is future hardening work
- [ ] JWT logout discards the client token but does not revoke an already stolen token server-side

## Final demo steps

1. Run `.\START_ALL.ps1` from the project root.
2. Open `http://127.0.0.1:5173`.
3. Log in.
4. Show Dashboard and Profiles.
5. Open Live Monitoring and acknowledge consent.
6. Start session and webcam.
7. Show face detection, real model status, expression, confidence, and smoothing window.
8. Save a stabilized observation and stop the session.
9. Show History and Analytics.
10. Open backend `/docs`.
11. Show `ai/services/expression_service.py`.
12. Show `ai/models/trained` metrics and confusion matrices.

## Evidence to capture for the final report

- Login and dashboard screenshot
- Profile and consent screenshot
- Live camera with face detected and real model status
- Saved observation in History
- Analytics distribution and trend charts
- FastAPI `/docs`
- AI service source and model name
- FER-2013 metrics JSON and confusion matrix CSV
- Automated test and frontend build output
