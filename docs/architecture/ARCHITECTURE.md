# Architecture

```
Browser (React + getUserMedia webcam)
        |  REST JSON (JWT)
        v
FastAPI backend (auth, profiles, sessions, observations, analytics)
        |  in-process call (Progress-1) / optional HTTP later
        v
AI module (OpenCV face detect + FER / DEMO MODE)
        |
        v
SQLite database (users, profiles, sessions, observations, reports, audit_logs)
```

## Design choices for a 6-week timeline

1. **Webcam in browser** — avoids shipping OpenCV camera loops on Windows; frames sent as JPEG base64 only when predicting.
2. **No continuous video storage** — privacy-first; save only caregiver-approved derived observations.
3. **SQLite** — zero-install local DB for Progress-1; swap `DATABASE_URL` for Postgres in cloud phase.
4. **Modular AI** — `ai/services/expression_service.py` is swappable; DEMO MODE is explicit.
5. **Optional layers** — `optional/cloud`, `optional/mobile`, `optional/blockchain` remain stubs until core is solid.

## Attention indicators (non-clinical)

| Code | Caregiver label |
|------|-----------------|
| `normal_observation` | Normal observation |
| `attention_recommended` | Attention recommended |
| `caregiver_check_recommended` | Caregiver check recommended |

Rules are heuristic thresholds on expression + confidence — **not** diagnoses.

## Security

- bcrypt password hashing  
- JWT bearer auth  
- Role checks (`caregiver` / `admin`)  
- Pydantic input validation  
- Secrets via `.env`
