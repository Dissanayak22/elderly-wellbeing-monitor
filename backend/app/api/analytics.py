from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import require_caregiver
from backend.app.models import AuditLog, ElderlyProfile, ExpressionObservation, Report, User
from backend.app.schemas import AnalyticsOut, ReportCreate, ReportOut

router = APIRouter(prefix="/api", tags=["analytics-reports"])


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db), user: User = Depends(require_caregiver)):
    rows = (
        db.query(ExpressionObservation)
        .filter(ExpressionObservation.caregiver_id == user.id)
        .all()
    )
    expression_distribution = Counter(r.expression for r in rows)
    attention_counts = Counter(r.attention_indicator for r in rows)
    daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        day = r.observed_at.strftime("%Y-%m-%d")
        daily[day][r.expression] += 1
    avg_conf = (sum(r.confidence for r in rows) / len(rows)) if rows else 0.0
    return AnalyticsOut(
        expression_distribution=dict(expression_distribution),
        daily_trends={d: dict(v) for d, v in daily.items()},
        observation_count=len(rows),
        average_confidence=round(avg_conf, 3),
        attention_counts=dict(attention_counts),
    )


@router.get("/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db), user: User = Depends(require_caregiver)):
    return (
        db.query(Report)
        .filter(Report.caregiver_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.post("/reports", response_model=ReportOut, status_code=201)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    profile = db.query(ElderlyProfile).filter(
        ElderlyProfile.id == body.elderly_id,
        ElderlyProfile.caregiver_id == user.id,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Elderly profile not found")

    observation_query = db.query(ExpressionObservation).filter(
        ExpressionObservation.caregiver_id == user.id,
        ExpressionObservation.elderly_id == body.elderly_id,
    )
    if body.period_start is not None:
        observation_query = observation_query.filter(
            ExpressionObservation.observed_at >= body.period_start
        )
    if body.period_end is not None:
        observation_query = observation_query.filter(
            ExpressionObservation.observed_at <= body.period_end
        )
    obs = observation_query.all()
    dist = Counter(o.expression for o in obs)
    summary = body.summary or (
        f"Monitoring report (research/support tool). Observations: {len(obs)}. "
        f"Expression distribution (AI predictions): {dict(dist)}. "
        "Not a medical diagnosis."
    )
    row = Report(
        elderly_id=body.elderly_id,
        caregiver_id=user.id,
        title=body.title,
        summary=summary,
        period_start=body.period_start,
        period_end=body.period_end or _utc_now_naive(),
    )
    db.add(row)
    db.add(
        AuditLog(
            user_id=user.id,
            action="create_report",
            entity_type="reports",
            entity_id=str(body.elderly_id),
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports/{report_id}/export")
def export_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    row = db.query(Report).filter(Report.id == report_id, Report.caregiver_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    text = (
        f"Title: {row.title}\n"
        f"Created: {row.created_at}\n"
        f"Period: {row.period_start} — {row.period_end}\n"
        f"Summary:\n{row.summary}\n\n"
        "DISCLAIMER: Research/support tool. Observable facial expression AI predictions only. "
        "Not a clinical diagnosis.\n"
    )
    return {"filename": f"report_{report_id}.txt", "content": text}
