from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.models import AuditLog, User
from backend.app.schemas import LoginRequest, RegisterRequest, Token, UserOut


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == body.email).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),

        # Security:
        # Do not allow the client to choose its own privileged role.
        role="caregiver",
    )

    db.add(user)
    db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="register",
            entity_type="user",
            entity_id=str(user.id),
        )
    )

    db.commit()
    db.refresh(user)

    token = create_access_token(
        user.email,
        {
            "role": user.role,
            "uid": user.id,
        },
    )

    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if (
        not user
        or not user.is_active
        or not verify_password(
            form_data.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(
        user.email,
        {
            "role": user.role,
            "uid": user.id,
        },
    )

    db.add(
        AuditLog(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=str(user.id),
        )
    )

    db.commit()

    return Token(access_token=token)


@router.post("/login/json", response_model=Token)
def login_json(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == body.email
    ).first()

    if (
        not user
        or not user.is_active
        or not verify_password(
            body.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(
        user.email,
        {
            "role": user.role,
            "uid": user.id,
        },
    )

    db.add(
        AuditLog(
            user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=str(user.id),
        )
    )

    db.commit()

    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
):
    return user


@router.post("/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.add(
        AuditLog(
            user_id=user.id,
            action="logout",
            entity_type="user",
            entity_id=str(user.id),
            detail=f"logout_at={datetime.utcnow().isoformat()}",
        )
    )

    db.commit()

    return {
        "message": "Logged out successfully. Discard the client token."
    }