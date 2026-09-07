"""Pydantic schemas — the API's request/response shapes. Part of the
model layer: these describe data, they don't contain business rules."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings


def _check_domain(email: str) -> str:
    if email.split("@")[-1].lower() != settings.ALLOWED_EMAIL_DOMAIN.lower():
        raise ValueError(
            f"Only @{settings.ALLOWED_EMAIL_DOMAIN} email addresses are accepted")
    return email


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: Optional[str] = Field(default=None, max_length=20)

    @field_validator("email")
    @classmethod
    def check_domain(cls, v):
        return _check_domain(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleSignInRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    status: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------- User ----------

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    profile_picture_url: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Employee ----------

class TodayStatusOut(BaseModel):
    date: date
    day_type: str
    is_having_lunch: Optional[bool]
    locked: bool
    cutoff_time: str
    message: Optional[str] = None


class ToggleLunchRequest(BaseModel):
    is_having_lunch: bool


class HistoryEntryOut(BaseModel):
    date: date
    day_type: str
    is_having_lunch: Optional[bool]

    class Config:
        from_attributes = True


class MonthlySummaryOut(BaseModel):
    month: str
    total_lunches: int
    total_skipped: int


# ---------- Admin ----------

class DailyCountOut(BaseModel):
    date: date
    day_type: str
    total_having_lunch: int
    names: list[str]


class EmployeeMonthlyTotal(BaseModel):
    user_id: int
    name: str
    email: str
    total_lunches: int


class MonthlyTotalsOut(BaseModel):
    month: str
    employees: list[EmployeeMonthlyTotal]


class DayHistoryOut(BaseModel):
    date: date
    day_type: str
    count: Optional[int]
    label: str


class MonthlyHistoryOut(BaseModel):
    month: str
    days: list[DayHistoryOut]


class DayDrilldownOut(BaseModel):
    date: date
    day_type: str
    names: list[str]


class ActivateRejectResponse(BaseModel):
    id: int
    status: str


class CutoffSettingsOut(BaseModel):
    cutoff_hour: int
    cutoff_minute: int
    cutoff_label: str


class UpdateCutoffRequest(BaseModel):
    cutoff_hour: int = Field(ge=0, le=23)
    cutoff_minute: int = Field(ge=0, le=59)
