import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.services.expression_service import clear_session_history, get_recognizer
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.deps import require_caregiver
from backend.app.models import AuditLog, ElderlyProfile, ExpressionObservation, MonitoringSession, User
from backend.app.schemas import (
    ObservationCreate,
    ObservationOut,
    PredictRequest,
    PredictResponse,
    SessionOut,
    SessionStart,
)
from backend.app.services.attention import compute_attention_indicator

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/sessions/start", response_model=SessionOut)
def start_session(
    body: SessionStart,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    profile = (
        db.query(ElderlyProfile)
        .filter(ElderlyProfile.id == body.elderly_id, ElderlyProfile.caregiver_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Elderly profile not found")

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    ended_at = _utc_now_naive()
    replaced_session_ids: list[str] = []
    prior_sessions = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.caregiver_id == user.id,
            MonitoringSession.status == "active",
        )
        .all()
    )
    for prior_session in prior_sessions:
        prior_session.status = "ended"
        prior_session.ended_at = ended_at
        replaced_session_ids.append(prior_session.session_id)
        db.add(
            AuditLog(
                user_id=user.id,
                action="auto_stop_session",
                entity_type="monitoring_sessions",
                entity_id=prior_session.session_id,
                detail=f"Replaced by {session_id}",
            )
        )

    row = MonitoringSession(
        session_id=session_id,
        elderly_id=profile.id,
        caregiver_id=user.id,
        status="active",
    )
    db.add(row)
    db.add(
        AuditLog(
            user_id=user.id,
            action="start_session",
            entity_type="monitoring_sessions",
            entity_id=session_id,
        )
    )
    db.commit()
    db.refresh(row)
    for replaced_session_id in replaced_session_ids:
        clear_session_history(replaced_session_id)
    return row


@router.post("/sessions/{session_id}/stop", response_model=SessionOut)
def stop_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    row = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.session_id == session_id,
            MonitoringSession.caregiver_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.status == "active":
        row.status = "ended"
        row.ended_at = _utc_now_naive()
        db.add(
            AuditLog(
                user_id=user.id,
                action="stop_session",
                entity_type="monitoring_sessions",
                entity_id=session_id,
            )
        )
        db.commit()
        db.refresh(row)
    clear_session_history(session_id)
    return row


@router.post("/predict", response_model=PredictResponse)
def predict_expression(
    body: PredictRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    session = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.session_id == body.session_id,
            MonitoringSession.caregiver_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Monitoring session is no longer active")

    recognizer = get_recognizer(get_settings().ai_demo_mode)
    result = recognizer.predict(body.image_base64, body.session_id)
    attention = compute_attention_indicator(result["expression"], result["confidence"])
    if not result["face_detected"]:
        attention = "normal_observation"

    return PredictResponse(
        expression=result["expression"],
        confidence=result["confidence"],
        raw_expression=result.get("raw_expression"),
        raw_confidence=result.get("raw_confidence"),
        smoothing_window=result.get("smoothing_window", 0),
        timestamp=result["timestamp"],
        session_id=result["session_id"],
        face_detected=result["face_detected"],
        attention_indicator=attention,
        demo_mode=result["demo_mode"],
        message=result["message"],
    )


@router.post("/observations", response_model=ObservationOut, status_code=201)
def save_observation(
    body: ObservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    profile = (
        db.query(ElderlyProfile)
        .filter(ElderlyProfile.id == body.elderly_id, ElderlyProfile.caregiver_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Elderly profile not found")
    session = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.session_id == body.session_id,
            MonitoringSession.caregiver_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Monitoring session is no longer active")
    if session.elderly_id != body.elderly_id:
        raise HTTPException(status_code=400, detail="Observation profile does not match the monitoring session")

    attention = compute_attention_indicator(body.expression, body.confidence)
    row = ExpressionObservation(
        session_id=body.session_id,
        elderly_id=body.elderly_id,
        caregiver_id=user.id,
        expression=body.expression,
        confidence=body.confidence,
        attention_indicator=attention,
        observed_at=body.observed_at,
        notes=body.notes,
    )
    db.add(row)
    db.add(
        AuditLog(
            user_id=user.id,
            action="save_observation",
            entity_type="expression_observations",
            entity_id=body.session_id,
            detail=f"{body.expression}:{body.confidence}",
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/observations", response_model=list[ObservationOut])
def list_observations(
    elderly_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    q = db.query(ExpressionObservation).filter(ExpressionObservation.caregiver_id == user.id)
    if elderly_id is not None:
        q = q.filter(ExpressionObservation.elderly_id == elderly_id)
    return q.order_by(ExpressionObservation.observed_at.desc()).limit(min(limit, 200)).all()
