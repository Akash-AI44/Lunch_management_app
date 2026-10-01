"""Sends Telegram notifications to employees who have linked their chat_id.
Each send is best-effort: one person's failed/blocked chat should never
stop the rest of the batch, so failures are caught and logged, not raised."""
import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import User, UserStatus


def send_telegram(chat_id: str, message: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        print(
            f"[notification_service] Telegram bot not configured — skipping {chat_id}")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url, json={"chat_id": chat_id, "text": message}, timeout=10)
        if not resp.ok:
            print(
                f"[notification_service] Telegram send failed for {chat_id}: {resp.text}")
    except Exception as exc:
        print(
            f"[notification_service] Failed to message Telegram chat {chat_id}: {exc}")


def notify_all_via_telegram(db: Session, message: str) -> None:
    users = db.query(User).filter(User.status == UserStatus.active).all()
    for user in users:
        if user.telegram_chat_id:
            send_telegram(user.telegram_chat_id, message)
