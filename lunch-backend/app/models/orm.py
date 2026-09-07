"""SQLAlchemy ORM entities — the persistence model. No business logic,
no request/response shaping; that belongs to the service and schema
layers respectively."""
import datetime as dt
import enum

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    employee = "employee"
    superadmin = "superadmin"


class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    rejected = "rejected"


class AuthProvider(str, enum.Enum):
    password = "password"
    google = "google"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(
        String(255))  # null for Google-only accounts
    auth_provider: Mapped[AuthProvider] = mapped_column(
        default=AuthProvider.password)
    role: Mapped[UserRole] = mapped_column(default=UserRole.employee)
    status: Mapped[UserStatus] = mapped_column(default=UserStatus.pending)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500))
    phone_number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    lunch_statuses: Mapped[list["LunchStatus"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class LunchStatus(Base):
    __tablename__ = "lunch_statuses"
    __table_args__ = (UniqueConstraint(
        "user_id", "date", name="uq_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    is_having_lunch: Mapped[bool]
    day_type: Mapped[str] = mapped_column(String(20))  # normal | friday
    locked_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="lunch_statuses")


class AppSettings(Base):
    """Single-row table (id is always 1) holding runtime-editable app
    settings. Currently just the lunch cutoff time. Living in the
    database (not .env) is what lets a superadmin change it from the
    UI without redeploying — and, crucially, means "locked" is computed
    fresh from whatever the cutoff is *right now*, not frozen at
    whatever it was when a given day's row first got checked."""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    cutoff_hour: Mapped[int]
    cutoff_minute: Mapped[int]
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
