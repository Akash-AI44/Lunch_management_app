import os
import uuid
from datetime import date as date_cls
from datetime import timedelta

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import LunchStatus, User
from app.services import settings_service
from app.services.exceptions import CutoffPassedError, InternalStateError, InvalidDateRangeError, InvalidImageTypeError, InvalidMonthFormatError, NoLunchFeatureError, NotOnLeaveError
from app.services.lunch_rules import cutoff_label, default_lunch_value, get_day_type, is_past_cutoff, parse_month, today_local
from app.services.exceptions import ServiceError

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
        "reason": row.reason,
        "locked": is_past_cutoff(today, cutoff_hour, cutoff_minute),
        "cutoff_time": cutoff_label(cutoff_hour, cutoff_minute), "message": None,
    }


def update_today_status(
    db: Session, user: User, is_having_lunch: bool, reason: str | None = None
) -> dict:
    today = today_local()
    day_type = get_day_type(today)
    cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)

    if day_type == "weekend":
        raise NoLunchFeatureError("There is no lunch feature on weekends.")
    if is_past_cutoff(today, cutoff_hour, cutoff_minute):
        raise CutoffPassedError(
            f"The {cutoff_label(cutoff_hour, cutoff_minute)} cutoff has passed — today's status is locked.")

    if not is_having_lunch and not reason:
        raise ServiceError("You have to tell the reason!")

    row = get_or_create_lunch_status(db, user.id, today)
    if row is None:
        raise InternalStateError("Could not resolve today's lunch status.")

    row.is_having_lunch = is_having_lunch
    row.reason = reason if not is_having_lunch else None
    db.commit()
    db.refresh(row)
    return {
        "date": today, "day_type": row.day_type, "is_having_lunch": row.is_having_lunch,
        "reason": row.reason,
        "locked": False, "cutoff_time": cutoff_label(cutoff_hour, cutoff_minute), "message": None,
    }


def apply_leave(
    db: Session, user: User, start_date: date_cls, end_date: date_cls, reason: str
) -> list[LunchStatus]:
    today = today_local()

    if end_date < start_date:
        raise InvalidDateRangeError("end_date cannot be before start_date.")
    if start_date < today:
        raise InvalidDateRangeError("Leave cannot be applied to a past date.")
    if not reason:
        raise ServiceError("You have to tell the reason!")

    # Only today's cutoff matters — future days aren't locked yet, no
    # matter what the current cutoff setting is.
    if start_date == today:
        cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)
        if is_past_cutoff(today, cutoff_hour, cutoff_minute):
            raise CutoffPassedError(
                f"The {cutoff_label(cutoff_hour, cutoff_minute)} cutoff has passed — "
                "today can't be included in a new leave request."
            )

    updated: list[LunchStatus] = []
    current = start_date
    while current <= end_date:
        day_type = get_day_type(current)
        if day_type != "weekend":
            row = get_or_create_lunch_status(db, user.id, current)
            if row is None:
                raise InternalStateError(
                    f"Could not resolve lunch status for {current}.")
            row.is_having_lunch = False
            row.reason = reason
            updated.append(row)
        current += timedelta(days=1)

    db.commit()
    for row in updated:
        db.refresh(row)

    return updated


def get_upcoming_leave(db: Session, user: User) -> list[LunchStatus]:
    today = today_local()
    return (
        db.query(LunchStatus)
        .filter(
            LunchStatus.user_id == user.id,
            LunchStatus.date >= today,
            LunchStatus.is_having_lunch == False,  # noqa: E712
        )
        .order_by(LunchStatus.date)
        .all()
    )


def cancel_leave_day(db: Session, user: User, target_date: date_cls) -> LunchStatus:
    today = today_local()

    if target_date < today:
        raise InvalidDateRangeError("Can't cancel leave for a past date.")

    if target_date == today:
        cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)
        if is_past_cutoff(today, cutoff_hour, cutoff_minute):
            raise CutoffPassedError(
                f"The {cutoff_label(cutoff_hour, cutoff_minute)} cutoff has passed — "
                "today's leave can't be cancelled anymore."
            )

    row = (
        db.query(LunchStatus)
        .filter(LunchStatus.user_id == user.id, LunchStatus.date == target_date)
        .first()
    )
    if row is None or row.is_having_lunch:
        raise NotOnLeaveError("This day isn't marked as leave.")

    default_value = default_lunch_value(row.day_type)
    if default_value is None:
        raise InternalStateError("Could not resolve the default lunch status.")
    row.is_having_lunch = default_value
    row.reason = None
    db.commit()
    db.refresh(row)
    return row


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
