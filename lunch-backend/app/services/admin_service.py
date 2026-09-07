"""Business logic for superadmin actions: activation, and daily/monthly
reporting. No FastAPI imports."""
import csv
import io
from calendar import monthrange
from datetime import date as date_cls

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.models.orm import LunchStatus, User, UserRole, UserStatus
from app.services import settings_service
from app.services.employee_service import get_or_create_lunch_status
from app.services.exceptions import InvalidMonthFormatError, UserNotFoundError, UserNotPendingError
from app.services.lunch_rules import cutoff_label, get_day_type, parse_month, today_local

__all__ = [
    "list_pending_users",
    "activate_user",
    "reject_user",
    "get_daily_count",
    "get_monthly_totals",
    "get_monthly_history",
    "get_day_drilldown",
    "export_daily_csv",
    "get_cutoff_settings",
    "update_cutoff_settings",
]


def _parse_month(month: str) -> tuple[int, int]:
    try:
        return parse_month(month)
    except ValueError:
        raise InvalidMonthFormatError("month must be in YYYY-MM format")


def list_active_employees(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.status == UserStatus.active, User.role == UserRole.employee)
        .order_by(User.name)
        .all()
    )


def list_pending_users(db: Session) -> list[User]:
    return db.query(User).filter(User.status == UserStatus.pending).order_by(User.created_at).all()


def _set_status(db: Session, user_id: int, new_status: UserStatus) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError("User not found.")
    if user.status != UserStatus.pending:
        raise UserNotPendingError(f"User is already {user.status.value}.")
    user.status = new_status
    db.commit()
    db.refresh(user)
    return user


def activate_user(db: Session, user_id: int) -> User:
    return _set_status(db, user_id, UserStatus.active)


def reject_user(db: Session, user_id: int) -> User:
    return _set_status(db, user_id, UserStatus.rejected)


def get_daily_count(db: Session, on: date_cls | None) -> dict:
    target_date = on or today_local()
    day_type = get_day_type(target_date)

    if day_type == "weekend":
        return {"date": target_date, "day_type": day_type, "total_having_lunch": 0, "names": []}

    employees = list_active_employees(db)
    for e in employees:
        get_or_create_lunch_status(db, e.id, target_date)

    rows = db.query(LunchStatus).filter(LunchStatus.date == target_date).all()
    having_lunch_ids = {r.user_id for r in rows if r.is_having_lunch}
    names = sorted(e.name for e in employees if e.id in having_lunch_ids)
    return {"date": target_date, "day_type": day_type, "total_having_lunch": len(names), "names": names}


def get_monthly_totals(db: Session, month: str) -> dict:
    year, mon = _parse_month(month)
    rows = (
        db.query(LunchStatus)
        .filter(extract("year", LunchStatus.date) == year, extract("month", LunchStatus.date) == mon)
        .all()
    )
    totals: dict[int, int] = {}
    for r in rows:
        if r.is_having_lunch:
            totals[r.user_id] = totals.get(r.user_id, 0) + 1

    employees = list_active_employees(db)
    result = [{"user_id": e.id, "name": e.name, "email": e.email,
               "total_lunches": totals.get(e.id, 0)} for e in employees]
    return {"month": month, "employees": result}


def get_monthly_history(db: Session, month: str) -> dict:
    year, mon = _parse_month(month)
    rows = (
        db.query(LunchStatus)
        .filter(extract("year", LunchStatus.date) == year, extract("month", LunchStatus.date) == mon)
        .all()
    )
    counts: dict[date_cls, int] = {}
    for r in rows:
        if r.is_having_lunch:
            counts[r.date] = counts.get(r.date, 0) + 1

    days = []
    for day_num in range(1, monthrange(year, mon)[1] + 1):
        d = date_cls(year, mon, day_num)
        day_type = get_day_type(d)
        if day_type == "weekend":
            days.append({"date": d, "day_type": day_type,
                        "count": None, "label": "Weekend"})
        else:
            count = counts.get(d, 0)
            label = f"{count} opted in" if day_type == "friday" else f"{count} getting lunch"
            days.append({"date": d, "day_type": day_type,
                        "count": count, "label": label})
    return {"month": month, "days": days}


def get_day_drilldown(db: Session, on: date_cls) -> dict:
    day_type = get_day_type(on)
    if day_type == "weekend":
        return {"date": on, "day_type": day_type, "names": []}

    rows = db.query(LunchStatus).filter(LunchStatus.date == on).all()
    having_lunch_ids = {r.user_id for r in rows if r.is_having_lunch}
    names = sorted(e.name for e in list_active_employees(db)
                   if e.id in having_lunch_ids)
    return {"date": on, "day_type": day_type, "names": names}


def export_daily_csv(db: Session, on: date_cls | None) -> tuple[str, str]:
    """Returns (filename, csv_text)."""
    target_date = on or today_local()
    day_type = get_day_type(target_date)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Name", "Email", "Having Lunch"])

    if day_type != "weekend":
        for e in list_active_employees(db):
            row = get_or_create_lunch_status(db, e.id, target_date)
            if row and row.is_having_lunch:
                writer.writerow([e.name, e.email, "Yes"])

    return f"lunch-list-{target_date.isoformat()}.csv", buffer.getvalue()


def get_cutoff_settings(db: Session) -> dict:
    cutoff_hour, cutoff_minute = settings_service.get_cutoff(db)
    return {"cutoff_hour": cutoff_hour, "cutoff_minute": cutoff_minute, "cutoff_label": cutoff_label(cutoff_hour, cutoff_minute)}


def update_cutoff_settings(db: Session, cutoff_hour: int, cutoff_minute: int) -> dict:
    cutoff_hour, cutoff_minute = settings_service.update_cutoff(
        db, cutoff_hour, cutoff_minute)
    return {"cutoff_hour": cutoff_hour, "cutoff_minute": cutoff_minute, "cutoff_label": cutoff_label(cutoff_hour, cutoff_minute)}
