from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.deps import require_caregiver
from backend.app.models import ElderlyProfile, ExpressionObservation, MonitoringSession, User
from backend.app.schemas import DashboardStats, ObservationOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DISCLAIMER = (
    "Research/support tool only. Shows AI predictions of observable facial expressions "
    "with confidence scores and caregiver attention indicators. "
    "Does not diagnose medical or mental-health conditions."
)


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    settings = get_settings()
    profiles = db.query(ElderlyProfile).filter(ElderlyProfile.caregiver_id == user.id).count()
    today = datetime.utcnow().date()
    sessions = (
        db.query(MonitoringSession)
        .filter(MonitoringSession.caregiver_id == user.id)
        .all()
    )
    today_sessions = sum(1 for s in sessions if s.started_at and s.started_at.date() == today)

    recent = (
        db.query(ExpressionObservation)
        .filter(ExpressionObservation.caregiver_id == user.id)
        .order_by(ExpressionObservation.observed_at.desc())
        .limit(8)
        .all()
    )
    all_obs = (
        db.query(ExpressionObservation)
        .filter(ExpressionObservation.caregiver_id == user.id)
        .all()
    )
    attention_counts = Counter(o.attention_indicator for o in all_obs)
    expression_distribution = Counter(o.expression for o in all_obs)

    return DashboardStats(
        total_elderly_profiles=profiles,
        today_sessions=today_sessions,
        recent_observations=[ObservationOut.model_validate(o) for o in recent],
        attention_counts=dict(attention_counts),
        expression_distribution=dict(expression_distribution),
        ai_demo_mode=settings.ai_demo_mode,
        disclaimer=DISCLAIMER,
    )
