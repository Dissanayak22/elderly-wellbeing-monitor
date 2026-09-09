# ✅ Localhost Setup & Startup Guide

## Quick Start (Recommended)

### Option 1: PowerShell (Windows - Recommended)
Run the all-in-one startup script:
```powershell
.\START_ALL.ps1
```

This will:
- ✓ Start Backend API on `http://127.0.0.1:8000`
- ✓ Start Frontend UI on `http://127.0.0.1:5173`
- ✓ Open both services in separate windows
- ✓ Show you all URLs and API documentation links

### Option 2: Individual Batch Files
Open **two separate command prompts** and run each:

**Terminal 1 - Backend API:**
```bash
start-backend.bat
```

**Terminal 2 - Frontend UI:**
```bash
start-frontend.bat
```

---

## URLs After Starting

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://127.0.0.1:5173 | Main application interface |
| **Backend API** | http://127.0.0.1:8000 | API server |
| **API Docs** | http://127.0.0.1:8000/docs | Interactive API documentation (Swagger) |
| **Alternative API Docs** | http://127.0.0.1:8000/redoc | ReDoc API documentation |

---

## Configuration Files

### `.env` (Project Root)
Main environment configuration. Includes:
- `CORS_ORIGINS` - Allowed frontend origins
- `AI_DEMO_MODE` - AI model mode (false = real model)
- `DATABASE_URL` - SQLite database path
- `API_PORT` - Backend port (8000)
- `FRONTEND_PORT` - Frontend port (5173)

### `frontend/vite.config.js`
Frontend build configuration:
- Host: `127.0.0.1`
- Port: `5173`
- Proxy: `/api` → `http://127.0.0.1:8000`

### `backend/app/core/config.py`
Backend FastAPI configuration:
- CORS origins configured from `.env`
- Database connection
- Security settings

---

## Troubleshooting

### Port Already in Use

If you see "Address already in use" error:

**For Backend (8000):**
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**For Frontend (5173):**
```bash
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

Or use the stop script:
```bash
STOP_SERVICES.bat
```

### Backend Not Connecting

1. Verify backend is running on `127.0.0.1:8000`:
   - Check terminal output shows "Uvicorn running on http://127.0.0.1:8000"
   - Visit http://127.0.0.1:8000/docs in browser

2. Check proxy in `frontend/vite.config.js`:
   ```javascript
   proxy: {
     "/api": "http://127.0.0.1:8000",
   }
   ```

3. Verify CORS in `.env`:
   ```
   CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
   ```

### Virtual Environment Issues

If backend won't start, ensure Python venv is set up:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then try `start-backend.bat` again.

### Node Modules Missing

If frontend won't start:

```bash
cd frontend
npm install
npm run dev
```

---

## Manual Testing

### Test Backend API
```bash
curl http://127.0.0.1:8000/api/health
```

Expected response:
```json
{"status": "ok"}
```

### Test Frontend → Backend Connection
Open browser console and check network tab:
- Go to http://127.0.0.1:5173
- Open DevTools (F12)
- Check "Network" tab for `/api/` requests
- Should see green 200 responses

---

## Production Deployment

For production, update:

1. `.env`:
   ```
   APP_ENV=production
   SECRET_KEY=<generate-secure-key>
   CORS_ORIGINS=<your-production-domain>
   ```

2. Backend: Use production ASGI server (Gunicorn, etc.)
3. Frontend: Build and deploy static files (`npm run build`)

---

## Architecture

```
┌─────────────────────────────────────────┐
│    User Browser                         │
│    http://127.0.0.1:5173                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│    Frontend (Vite + React)              │
│    Port 5173 (127.0.0.1)                │
│    - Serves UI                          │
│    - Proxies /api to backend            │
└────────────┬────────────────────────────┘
             │ /api proxy
             ▼
┌─────────────────────────────────────────┐
│    Backend (FastAPI)                    │
│    Port 8000 (127.0.0.1)                │
│    - REST API                           │
│    - Database (SQLite)                  │
│    - AI Services                        │
└─────────────────────────────────────────┘
```

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `.\START_ALL.ps1` | Start everything (PowerShell) |
| `start-backend.bat` | Start just backend |
| `start-frontend.bat` | Start just frontend |
| `STOP_SERVICES.bat` | Stop all services |
| `npm run dev` | Start frontend (from frontend folder) |
| `npm run build` | Build frontend for production |
| `npm test` | Run frontend tests |

---

## Need Help?

Check these logs for errors:
- **Backend**: Terminal where backend is running
- **Frontend**: Terminal where frontend is running
- **Browser Console**: F12 in browser, Console tab
- **Network Tab**: F12 in browser, Network tab (check `/api/` requests)

