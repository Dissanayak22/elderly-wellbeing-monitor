from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


ExpressionLabel = Literal[
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral",
]


def _utc_naive_input(value: datetime | None) -> datetime | None:
    """Require an explicit offset and normalize API input for SQLite storage."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a UTC offset, for example Z or +05:30")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_aware_output(value: datetime | None) -> datetime | None:
    """Treat database-naive timestamps as UTC and serialize them unambiguously."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["caregiver"] = "caregiver"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class ElderlyCreate(BaseModel):
    elderly_code: str = Field(min_length=2, max_length=64)
    full_name: str = Field(min_length=2, max_length=255)
    age: Optional[int] = Field(default=None, ge=1, le=130)
    notes: Optional[str] = None


class ElderlyOut(BaseModel):
    id: int
    elderly_code: str
    full_name: str
    age: Optional[int]
    notes: Optional[str]
    caregiver_id: int
    created_at: datetime

    _normalize_created_at = field_validator("created_at", mode="after")(_utc_aware_output)

    model_config = {"from_attributes": True}


class SessionStart(BaseModel):
    elderly_id: int


class SessionOut(BaseModel):
    id: int
    session_id: str
    elderly_id: int
    caregiver_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    status: str

    _normalize_session_times = field_validator("started_at", "ended_at", mode="after")(
        _utc_aware_output
    )

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    image_base64: str = Field(min_length=32, max_length=2_000_000)
    session_id: str


class PredictResponse(BaseModel):
    expression: str
    confidence: float
    raw_expression: str | None = None
    raw_confidence: float | None = None
    smoothing_window: int = 0
    timestamp: str
    session_id: str
    face_detected: bool
    attention_indicator: str
    demo_mode: bool
    message: str


class ObservationCreate(BaseModel):
    session_id: str
    elderly_id: int
    expression: ExpressionLabel
    confidence: float = Field(ge=0, le=1)
    observed_at: datetime
    notes: Optional[str] = None

    @field_validator("expression", mode="before")
    @classmethod
    def normalize_expression(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    _normalize_observed_at = field_validator("observed_at", mode="after")(_utc_naive_input)


class ObservationOut(BaseModel):
    id: int
    session_id: str
    elderly_id: int
    caregiver_id: int
    expression: str
    confidence: float
    attention_indicator: str
    observed_at: datetime
    notes: Optional[str]
    created_at: datetime

    _normalize_observation_times = field_validator("observed_at", "created_at", mode="after")(
        _utc_aware_output
    )

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_elderly_profiles: int
    today_sessions: int
    recent_observations: list[ObservationOut]
    attention_counts: dict[str, int]
    expression_distribution: dict[str, int]
    ai_demo_mode: bool
    disclaimer: str


class ReportCreate(BaseModel):
    elderly_id: int
    title: str = Field(min_length=1, max_length=255)
    summary: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    _normalize_report_input_times = field_validator("period_start", "period_end", mode="after")(
        _utc_naive_input
    )

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class ReportOut(BaseModel):
    id: int
    elderly_id: int
    caregiver_id: int
    title: str
    summary: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    created_at: datetime

    _normalize_report_output_times = field_validator(
        "period_start",
        "period_end",
        "created_at",
        mode="after",
    )(_utc_aware_output)

    model_config = {"from_attributes": True}


class AnalyticsOut(BaseModel):
    expression_distribution: dict[str, int]
    daily_trends: dict[str, dict[str, int]]
    observation_count: int
    average_confidence: float
    attention_counts: dict[str, int]
