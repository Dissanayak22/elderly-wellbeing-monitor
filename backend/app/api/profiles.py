from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import require_caregiver
from backend.app.models import AuditLog, ElderlyProfile, User
from backend.app.schemas import ElderlyCreate, ElderlyOut

router = APIRouter(prefix="/api/elderly", tags=["elderly"])


@router.get("", response_model=list[ElderlyOut])
def list_elderly(db: Session = Depends(get_db), user: User = Depends(require_caregiver)):
    return (
        db.query(ElderlyProfile)
        .filter(ElderlyProfile.caregiver_id == user.id)
        .order_by(ElderlyProfile.full_name)
        .all()
    )


@router.post("", response_model=ElderlyOut, status_code=status.HTTP_201_CREATED)
def create_elderly(
    body: ElderlyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_caregiver),
):
    exists = db.query(ElderlyProfile).filter(ElderlyProfile.elderly_code == body.elderly_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="Elderly code already exists")
    profile = ElderlyProfile(
        elderly_code=body.elderly_code,
        full_name=body.full_name,
        age=body.age,
        notes=body.notes,
        caregiver_id=user.id,
    )
    db.add(profile)
    db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="create_elderly",
            entity_type="elderly_profiles",
            entity_id=str(profile.id),
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{elderly_id}", response_model=ElderlyOut)
def get_elderly(elderly_id: int, db: Session = Depends(get_db), user: User = Depends(require_caregiver)):
    profile = (
        db.query(ElderlyProfile)
        .filter(ElderlyProfile.id == elderly_id, ElderlyProfile.caregiver_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
