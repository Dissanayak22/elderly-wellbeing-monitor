# Testing Results

## Automated checks

The final verification suite includes:

- Backend tests: `9 passed`
- Frontend tests: `2 passed`
- Frontend production build: passed with Vite
- PowerShell launcher syntax: passed
- Backend health endpoint: `200 OK`
- Frontend root URL: `200 OK`

Backend tests cover health, login, dashboard access, session prediction handling, observation saving, real-mode unavailable-model behavior, stopped-session rejection, and session/profile ownership validation.

## Manual demonstration checks

1. Start the backend on port 8000.
2. Start the frontend on port 5173.
3. Log in as a caregiver or register a new account.
4. Create/select an elderly profile.
5. Acknowledge consent, start a session, and grant webcam permission.
6. Confirm face detected/no-face messaging and real model status.
7. Confirm raw and smoothed expression/confidence values.
8. Save a stabilized observation, then stop the session.
9. Confirm the observation appears in History and Analytics.
10. Open `/docs` and show the AI source and preserved training results.

## Known test gaps

There is no automated browser test for webcam permissions or full React route navigation. Real model inference requires the Hugging Face model to be cached or downloaded and a camera frame containing a detectable face. These are manual demo checks.
