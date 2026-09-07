"""Runtime-editable app settings, backed by a single-row database table
instead of .env — this is what lets a superadmin change the lunch
cutoff from the UI and have it take effect immediately, for everyone,
without a redeploy or restart."""
from sqlalchemy.orm import Session

from app.core.config import settings as env_settings
from app.models.orm import AppSettings
from app.services.exceptions import ServiceError

SETTINGS_ROW_ID = 1


class InvalidCutoffError(ServiceError):
    status_code = 422


def _get_or_seed_row(db: Session) -> AppSettings:
    """Lazily creates the single settings row on first access, seeded
    from the .env defaults — so a fresh database behaves exactly like
    before any admin has ever changed anything."""
    row = db.query(AppSettings).filter(
        AppSettings.id == SETTINGS_ROW_ID).first()
    if row is None:
        row = AppSettings(
            id=SETTINGS_ROW_ID,
            cutoff_hour=env_settings.CUTOFF_HOUR,
            cutoff_minute=env_settings.CUTOFF_MINUTE,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_cutoff(db: Session) -> tuple[int, int]:
    row = _get_or_seed_row(db)
    return row.cutoff_hour, row.cutoff_minute


def update_cutoff(db: Session, cutoff_hour: int, cutoff_minute: int) -> tuple[int, int]:
    if not (0 <= cutoff_hour <= 23):
        raise InvalidCutoffError("cutoff_hour must be between 0 and 23.")
    if not (0 <= cutoff_minute <= 59):
        raise InvalidCutoffError("cutoff_minute must be between 0 and 59.")

    row = _get_or_seed_row(db)
    row.cutoff_hour = cutoff_hour
    row.cutoff_minute = cutoff_minute
    db.commit()
    db.refresh(row)
    return row.cutoff_hour, row.cutoff_minute
