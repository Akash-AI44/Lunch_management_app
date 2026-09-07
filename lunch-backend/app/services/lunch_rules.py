"""Core business rules from the requirements doc (section 3.5):

- Monday-Thursday: opt-out. Defaults to having lunch (True). Employee may
  uncheck before the cutoff.
- Friday: opt-in (reversed). Defaults to NOT having lunch (False). Employee
  may check the box before the cutoff to opt in.
- Saturday/Sunday: no lunch feature at all. No record is created/shown.
- Cutoff time is runtime-editable by a superadmin (see settings_service /
  AppSettings) — enforced here, server-side, in a fixed configured
  timezone, never trusted from the client. Because it's read fresh from
  the database on every request rather than baked in at startup, raising
  the cutoff immediately re-opens today for everyone, with no per-day
  "permanently locked" flag to fight against.

Kept as pure functions with no DB/HTTP dependency so they're trivial to
unit test in isolation. cutoff_hour/cutoff_minute are passed in by the
caller (which fetches them from settings_service) rather than read from
a module-level singleton here.
"""
from datetime import date as date_cls
from datetime import datetime, time

from zoneinfo import ZoneInfo

from app.core.config import settings

TZ = ZoneInfo(settings.TIMEZONE)
FRIDAY, SATURDAY, SUNDAY = 4, 5, 6


def today_local() -> date_cls:
    return datetime.now(TZ).date()


def get_day_type(d: date_cls) -> str:
    weekday = d.weekday()
    if weekday in (SATURDAY, SUNDAY):
        return "weekend"
    if weekday == FRIDAY:
        return "friday"
    return "normal"


def default_lunch_value(day_type: str) -> bool | None:
    return {"normal": True, "friday": False, "weekend": None}[day_type]


def is_past_cutoff(d: date_cls, cutoff_hour: int, cutoff_minute: int) -> bool:
    cutoff = datetime.combine(d, time(cutoff_hour, cutoff_minute), tzinfo=TZ)
    return datetime.now(TZ) >= cutoff


def cutoff_label(cutoff_hour: int, cutoff_minute: int) -> str:
    return f"{cutoff_hour:02d}:{cutoff_minute:02d}"


def parse_month(month: str) -> tuple[int, int]:
    """Parses a "YYYY-MM" string. Raises ValueError on bad format —
    callers (services) translate that into InvalidMonthFormatError."""
    year_str, mon_str = month.split("-")
    year, mon = int(year_str), int(mon_str)
    if not (1 <= mon <= 12):
        raise ValueError(f"invalid month: {month}")
    return year, mon
