"""Business logic for an employee's own lunch status, history, and
profile. No FastAPI imports — file uploads are accepted as raw
(filename, content_type, content) rather than UploadFile, so this stays
testable without the web framework."""
import os
import uuid
from datetime import date as date_cls

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import LunchStatus, User
from app.services import settings_service
from app.services.exceptions import CutoffPassedError, InternalStateError, InvalidImageTypeError, InvalidMonthFormatError, NoLunchFeatureError
from app.services.lunch_rules import cutoff_label, default_lunch_value, get_day_type, is_past_cutoff, parse_month, today_local

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _parse_month(month: str) -> tuple[int, int]:
    try:
        return parse_month(month)
    except ValueError:
        raise InvalidMonthFormatError("month must be in YYYY-MM format")


def get_or_create_lunch_status(db: Session, user_id: int, d: date_cls) -> LunchStatus | None:
    """Lazily creates the day's record with the correct default. Returns
    None on weekends, since no record/feature exists for those days.

    Does NOT decide "locked" here — that's computed fresh from the
    *current* cutoff setting every time it's needed (see
    get_today_status/update_today_status), not baked into this row.
    That's deliberate: it's what lets a superadmin raise the cutoff and
    immediately re-open today for everyone, with nothing per-row to
    fight against."""
    day_type = get_day_type(d)
    if day_type == "weekend":
        return None

    row = db.query(LunchStatus).filter(LunchStatus.user_id ==
                                       user_id, LunchStatus.date == d).first()
    if row:
        return row

    row = LunchStatus(
        user_id=user_id,
        date=d,
        is_having_lunch=default_lunch_value(day_type),
        day_type=day_type,
        locked_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_today_status(db: Session, user: User) -> dict:
    today = today_local()
    day_type = get_day_type(today)
    cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)

    if day_type == "weekend":
        return {
            "date": today, "day_type": "weekend", "is_having_lunch": None, "locked": True,
            "cutoff_time": cutoff_label(cutoff_hour, cutoff_minute), "message": "It's the weekend — no lunch feature today.",
        }

    row = get_or_create_lunch_status(db, user.id, today)
    if row is None:
        raise InternalStateError("Could not resolve today's lunch status.")
    return {
        "date": today, "day_type": row.day_type, "is_having_lunch": row.is_having_lunch,
        "locked": is_past_cutoff(today, cutoff_hour, cutoff_minute),
        "cutoff_time": cutoff_label(cutoff_hour, cutoff_minute), "message": None,
    }


def update_today_status(db: Session, user: User, is_having_lunch: bool) -> dict:
    today = today_local()
    day_type = get_day_type(today)
    cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)

    if day_type == "weekend":
        raise NoLunchFeatureError("There is no lunch feature on weekends.")
    if is_past_cutoff(today, cutoff_hour, cutoff_minute):
        raise CutoffPassedError(
            f"The {cutoff_label(cutoff_hour, cutoff_minute)} cutoff has passed — today's status is locked.")

    row = get_or_create_lunch_status(db, user.id, today)
    if row is None:
        raise InternalStateError("Could not resolve today's lunch status.")

    row.is_having_lunch = is_having_lunch
    db.commit()
    db.refresh(row)
    return {
        "date": today, "day_type": row.day_type, "is_having_lunch": row.is_having_lunch,
        "locked": False, "cutoff_time": cutoff_label(cutoff_hour, cutoff_minute), "message": None,
    }


def get_history(db: Session, user: User, month: str) -> list[LunchStatus]:
    year, mon = _parse_month(month)
    return (
        db.query(LunchStatus)
        .filter(LunchStatus.user_id == user.id, extract("year", LunchStatus.date) == year, extract("month", LunchStatus.date) == mon)
        .order_by(LunchStatus.date)
        .all()
    )


def get_summary(db: Session, user: User, month: str) -> dict:
    rows = get_history(db, user, month)
    total_lunches = sum(1 for r in rows if r.is_having_lunch)
    total_skipped = sum(1 for r in rows if not r.is_having_lunch)
    return {"month": month, "total_lunches": total_lunches, "total_skipped": total_skipped}


def save_profile_picture(db: Session, user: User, filename: str, content_type: str, content: bytes) -> User:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImageTypeError(
            "Only JPEG, PNG, or WEBP images are allowed.")

    folder = os.path.join(settings.MEDIA_ROOT, "profile_pictures")
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(filename or "")[1] or ".jpg"
    saved_name = f"user-{user.id}-{uuid.uuid4().hex[:8]}{ext}"

    with open(os.path.join(folder, saved_name), "wb") as f:
        f.write(content)

    user.profile_picture_url = f"/media/profile_pictures/{saved_name}"
    db.commit()
    db.refresh(user)
    return user
