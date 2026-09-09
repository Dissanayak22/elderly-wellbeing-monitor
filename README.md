# AI-Based Elderly Wellbeing Monitoring and Facial Expression Recognition System

**Research / caregiver support tool** — not a medical diagnostic system.  
The system reports **observable facial expression** predictions with **confidence scores** and **caregiver attention indicators** only.

---

## Project overview

A software-only, laptop-webcam system for caregivers to:

1. Authenticate and manage elderly profiles  
2. Run live monitoring sessions (webcam → face detection → expression prediction)  
3. Save and review observations  
4. View analytics, attention indicators, and simple reports  

**Hardware constraint:** laptop built-in webcam (optional microphone). No ESP32, Arduino, IoT sensors, or robotics.

---

## Architecture

```
┌─────────────────┐     REST/JSON      ┌─────────────────┐
│  React Frontend │ ─────────────────► │  FastAPI Backend│
│  (Webcam in     │                    │  Auth • CRUD    │
│   browser)      │ ◄───────────────── │  Sessions       │
└────────┬────────┘                    └────────┬────────┘
         │ frame (base64 JPEG)                  │
         │                                      ▼
         │                             ┌─────────────────┐
         └────────────────────────────►│  Python AI Svc  │
                                       │  OpenCV + FER   │
                                       └────────┬────────┘
                                                ▼
                                       ┌─────────────────┐
                                       │  SQLite / DB    │
                                       └─────────────────┘
```

Optional later layers (scaffolded under `optional/`):

- **Cloud** — deploy API + managed DB  
- **Mobile** — React Native / PWA caregiver app  
- **Blockchain** — append-only audit hashes (modular, off by default)

---

## Folder structure

```
elderly-wellbeing-monitor/
├── frontend/          # React + Vite UI
├── backend/           # FastAPI REST API
├── ai/                # Face detection + FER (+ demo mode)
├── database/          # Schema, seeds, migrations notes
├── docs/              # Architecture, API, screenshots
├── optional/          # Cloud / mobile / blockchain stubs
├── .env.example
└── README.md
```

---

## Implementation plan (≈ 6 weeks)

| Week | Focus | Deliverable |
|------|--------|-------------|
| 1 | Progress-1 prototype | Login, dashboard, webcam, face+expression, save & list observations |
| 2 | Profiles, sessions, history, attention rules | Full caregiver CRUD + history UI |
| 3 | Analytics & reports | Charts, CSV/PDF-style export |
| 4 | Hardening | Tests, privacy copy, AI evaluation harness |
| 5 | Cloud + mobile prep | Deploy notes, PWA/mobile stub |
| 6 | Optional blockchain + polish | Audit module, docs, demo video |

### Progress-1 (this baseline) must show

1. Login / dashboard  
2. Webcam access (browser)  
3. Face detection  
4. Facial-expression prediction  
5. Confidence score  
6. Save observation  
7. View recent observations  

---

## Supported expressions

`happy` · `sad` · `neutral` · `angry` · `fear` · `surprise` · `disgust`

Wording used in UI/API: *observable facial expression*, *AI prediction*, *confidence score*, *caregiver attention indicator*.

---

## Quick start (Windows + VS Code)

### Prerequisites

- Python 3.10+  
- Node.js 18+  
- Git  

### 1. Clone / open project

```powershell
cd D:\elderly-wellbeing-monitor
code .
```

> **Note:** Canonical project path is `D:\elderly-wellbeing-monitor` (C: drive was low on free space). A copy may also exist under Documents.

### 2. Environment

```powershell
copy .env.example .env
```

### 3. Backend + AI

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
pip install -r ai\requirements.txt
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Frontend

```powershell
cd frontend
npm install
npm.cmd run dev
```

Open http://localhost:8080  

> If your PowerShell execution policy allows `npm`, `npm run dev` works too.
> `npm.cmd run dev` avoids the common "running scripts is disabled" error caused by
> PowerShell resolving `npm` to its blocked `npm.ps1` wrapper.

**Demo caregiver login**

- Email: `caregiver@demo.example.com`  
- Password: `Caregiver123!`

### Demo mode (AI)

If OpenCV/FER weights are unavailable, set in `.env`:

```
AI_DEMO_MODE=true
```

Demo mode is clearly labeled in the UI. Prefer `AI_DEMO_MODE=false` once the model is installed.

---

## Database

SQLite file default: `database/app.db`  

Tables: `users`, `elderly_profiles`, `monitoring_sessions`, `expression_observations`, `reports`, `audit_logs`  

See `database/schema.sql` and `docs/api/API.md`.

---

## Testing

```powershell
# Backend
cd backend
pytest

# AI evaluation harness
cd ..\ai
pytest
python -m evaluation.run_eval --help
```

---

## Privacy & ethics

- Webcam frames are processed for inference; **continuous video is not stored**.  
- Only derived observation records (expression, confidence, timestamps, session IDs) are persisted when the caregiver saves.  
- Consent / privacy notice is shown in Settings and at first login.  
- This is a **research and caregiver support tool**, not a clinical diagnosis system.

---

## Screenshots

Place UI captures in `docs/screenshots/` (see placeholder notes there).

---

## License

Academic / educational use for final-year project demonstration.
