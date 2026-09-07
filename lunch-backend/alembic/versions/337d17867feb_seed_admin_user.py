"""seed admin user

Revision ID: 5351b5509b48
Revises: d3339b397968
Create Date: 2026-08-26 14:15:41.564331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5351b5509b48'
down_revision: Union[str, Sequence[str], None] = 'd3339b397968'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight, migration-local view of the users table — deliberately
# not importing app.models.orm.User here. Migrations should stay
# independent of the current state of your model classes, which will
# keep changing over the app's life; this file should keep working
# and mean the same thing even years from now.
users_table = sa.table(
    "users",
    sa.column("name", sa.String),
    sa.column("email", sa.String),
    sa.column("password_hash", sa.String),
    sa.column("auth_provider", sa.String),
    sa.column("role", sa.String),
    sa.column("status", sa.String),
)


def upgrade() -> None:
    """Seed exactly one superadmin account, from SEED_ADMIN_* in .env.

    Deliberately idempotent: safe to run again (e.g. after a `alembic
    downgrade` + `upgrade` cycle during testing) without erroring or
    creating a duplicate, and it backs off harmlessly if a user with
    that email already exists for any reason.
    """
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from app.core.config import settings
    from app.core.security import hash_password

    bind = op.get_bind()

    existing = bind.execute(
        sa.text("SELECT id FROM users WHERE lower(email) = lower(:email)"),
        {"email": settings.SEED_ADMIN_EMAIL},
    ).first()
    if existing is not None:
        print(
            f"[seed_admin_user] A user with email {settings.SEED_ADMIN_EMAIL!r} already exists — skipping.")
        return

    op.bulk_insert(
        users_table,
        [
            {
                "name": settings.SEED_ADMIN_NAME,
                "email": settings.SEED_ADMIN_EMAIL,
                "password_hash": hash_password(settings.SEED_ADMIN_PASSWORD),
                "auth_provider": "password",
                "role": "superadmin",
                "status": "active",
            }
        ],
    )
    print(f"[seed_admin_user] Created superadmin {settings.SEED_ADMIN_EMAIL!r}. "
          f"Log in and change the password immediately.")


def downgrade() -> None:
    """Removes the seeded admin by email — only if its role is still
    superadmin, so this never deletes an account that happened to reuse
    the same email after being changed by hand."""
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from app.core.config import settings

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM users WHERE lower(email) = lower(:email) AND role = 'superadmin'"
        ),
        {"email": settings.SEED_ADMIN_EMAIL},
    )
