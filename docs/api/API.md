# API documentation (Progress-1)

Base URL: `http://127.0.0.1:8000`

Interactive docs: `/docs` (Swagger) · `/redoc`

Auth: `Authorization: Bearer <token>` after login.

## Auth

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/auth/login` | form `username`, `password` | OAuth2 form |
| POST | `/api/auth/login/json` | `{email, password}` | JSON login |
| GET | `/api/auth/me` | — | Current user |
| POST | `/api/auth/logout` | — | Audit log + client discards token |

## Dashboard

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/dashboard/stats` | Profiles, sessions, recent obs, charts data |

## Elderly profiles

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/elderly` | List |
| POST | `/api/elderly` | Create |
| GET | `/api/elderly/{id}` | Detail |

## Monitoring / AI

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/monitoring/sessions/start` | `{elderly_id}` → `session_id` |
| POST | `/api/monitoring/sessions/{session_id}/stop` | End session |
| POST | `/api/monitoring/predict` | `{image_base64, session_id}` |
| POST | `/api/monitoring/observations` | Save derived result |
| GET | `/api/monitoring/observations` | History |

### Predict response shape

```json
{
  "expression": "happy",
  "confidence": 0.91,
  "timestamp": "2026-08-16T14:00:00+00:00",
  "session_id": "sess_abc123",
  "face_detected": true,
  "attention_indicator": "normal_observation",
  "demo_mode": true,
  "message": "..."
}
```

## Analytics & reports

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/analytics` | Distribution, trends, avg confidence |
| GET/POST | `/api/reports` | List / create |
| GET | `/api/reports/{id}/export` | Text export |

## Health

`GET /api/health`
