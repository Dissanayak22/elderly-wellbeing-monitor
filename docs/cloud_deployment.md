# Cloud deployment notes

This project is prepared for cloud deployment without changing its working local setup or replacing the real AI model.

## Current architecture
- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite for local development
- AI: OpenCV + Hugging Face facial-expression model + 5-frame smoothing
- Auth: JWT-based caregiver authentication

## Cloud deployment intent
- Backend target: Render
- Frontend target: Vercel

## Backend readiness
- The backend should be started with:
  python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
- The app reads the port from environment when available via the Render-provided PORT value.
- Local default behavior still runs on 127.0.0.1:8000.
- CORS is configured from FRONTEND_ORIGINS and still preserves localhost origins.
- AI_DEMO_MODE remains false in production and the real model remains active.

## Frontend readiness
- The frontend should use VITE_API_BASE_URL for the backend base URL.
- Local default remains http://127.0.0.1:8000.
- A production Render URL can be set through environment variables without changing source code.
- The existing local development proxy is still valid and should not be removed.

## Environment variables
### Backend
- SECRET_KEY=replace-with-a-long-random-secret
- APP_ENV=production
- FRONTEND_ORIGINS=https://your-app.vercel.app,http://127.0.0.1:5173,http://localhost:5173
- DATABASE_URL=sqlite:///./database/app.db
- AI_DEMO_MODE=false

### Frontend
- VITE_API_BASE_URL=https://your-render-backend.onrender.com

## Important note about SQLite
SQLite is fine for local development and may remain in place for this project. Cloud hosting may later require PostgreSQL or persistent storage for production-grade persistence.

## Deployment blockers / notes
- The real AI model remains in use; no demo replacement is enabled.
- The database has not been migrated to PostgreSQL yet.
- .env files remain local-only and are ignored by git.
- No production deployment has been performed yet.
