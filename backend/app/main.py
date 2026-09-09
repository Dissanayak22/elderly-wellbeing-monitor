import sys
from contextlib import asynccontextmanager
from importlib import import_module
from platform import python_version
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api import analytics, auth, dashboard, monitoring, profiles
from backend.app.core.config import get_settings
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models import ElderlyProfile, User
from ai.services.expression_service import get_recognizer_status

settings = get_settings()


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        # Main caregiver account
        user = db.query(User).filter(User.email == "caregiver@wellbeing.care").first()
        if not user:
            user = User(
                email="caregiver@wellbeing.care",
                full_name="Kveee . s",
                hashed_password=hash_password("Caregiver123!"),
                role="caregiver",
            )
            db.add(user)
            db.flush()          

        # Legacy alias for seamless backwards compatibility
        alias_user = db.query(User).filter(User.email == "caregiver@demo.example.com").first()
        if not alias_user:
            alias_user = User(
                email="caregiver@demo.example.com",
                full_name="Kveee . s",
                hashed_password=hash_password("Caregiver123!"),
                role="caregiver",
            )
            db.add(alias_user)
            db.flush()

        if not db.query(ElderlyProfile).filter(ElderlyProfile.caregiver_id == user.id).first():
            db.add(
                ElderlyProfile(
                    elderly_code="ELD-001",
                    full_name="Alex Rivera",
                    age=72,
                    notes="Resident profile — scheduled daily facial expression observation.",
                    caregiver_id=user.id,
                )
            )
            db.add(
                ElderlyProfile(
                    elderly_code="ELD-002",
                    full_name="Jordan Lee",
                    age=68,
                    notes="Resident profile — scheduled daily facial expression observation.",
                    caregiver_id=user.id,
                )
            )
        if not db.query(ElderlyProfile).filter(ElderlyProfile.caregiver_id == alias_user.id).first():
            db.add(
                ElderlyProfile(
                    elderly_code="ELD-001-A",
                    full_name="Alex Rivera",
                    age=72,
                    notes="Resident profile — scheduled daily facial expression observation.",
                    caregiver_id=alias_user.id,
                )
            )
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    Path(ROOT / "database").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if settings.app_env.lower() != "production" and settings.seed_demo_data:
        seed_demo_data()


def validate_runtime_security() -> None:
    if settings.app_env.lower() == "production":
        known_development_secrets = {
            "dev-secret-change-me",
            "change-me-to-a-long-random-string",
            "dev-progress1-secret-change-before-production",
        }
        if settings.secret_key in known_development_secrets or len(settings.secret_key) < 32:
            raise RuntimeError("Production requires a unique SECRET_KEY with at least 32 characters")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_security()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-Based Elderly Wellbeing Monitoring API. "
        "Reports observable facial expression predictions for caregiver support. "
        "Not a medical diagnostic system."
    ),
    version="0.1.0-progress1",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in settings.effective_frontend_origins.split(",")
    if origin.strip()
]
if not origins:
    origins = ["http://127.0.0.1:5173", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(profiles.router)
app.include_router(monitoring.router)
app.include_router(analytics.router)


def _database_health() -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        return {
            "ready": False,
            "driver": settings.database_url.split(":", 1)[0],
            "error": type(exc).__name__,
        }
    return {
        "ready": True,
        "driver": settings.database_url.split(":", 1)[0],
    }


def _dependency_health() -> dict[str, object]:
    required_modules = {
        "numpy": "numpy",
        "opencv": "cv2",
    }
    if not settings.ai_demo_mode:
        required_modules.update(
            {
                "pillow": "PIL",
                "torch": "torch",
                "torchvision": "torchvision",
                "transformers": "transformers",
            }
        )
    available: dict[str, bool] = {}
    versions: dict[str, str] = {}
    errors: dict[str, str] = {}
    for name, module_name in required_modules.items():
        try:
            module = import_module(module_name)
            available[name] = True
            versions[name] = str(getattr(module, "__version__", "installed"))
        except Exception as exc:
            available[name] = False
            errors[name] = type(exc).__name__
    missing = [name for name, installed in available.items() if not installed]
    return {
        "ready": not missing,
        "available": available,
        "versions": versions,
        "missing": missing,
        "errors": errors,
    }


@app.get("/api/health")
def health(response: Response):
    database = _database_health()
    dependencies = _dependency_health()
    ai = get_recognizer_status(settings.ai_demo_mode)
    ready = bool(database["ready"] and dependencies["ready"])
    fully_ready = bool(ready and ai["ready"])
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "error"
    elif ai["state"] == "unavailable":
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return {
        "status": overall_status,
        "ready": ready,
        "fully_ready": fully_ready,
        "app": settings.app_name,
        "ai_demo_mode": settings.ai_demo_mode,
        "database_ready": database["ready"],
        "dependencies_ready": dependencies["ready"],
        "ai_ready": ai["ready"],
        "ai_runtime_status": ai["state"],
        "checks": {
            "database": database,
            "dependencies": dependencies,
            "ai": ai,
        },
        "runtime": {
            "environment": settings.app_env,
            "python": python_version(),
        },
        "disclaimer": "Research/support tool — not a medical diagnosis system.",
    }
