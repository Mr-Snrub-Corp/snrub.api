"""Database seed runner. Only runs in development.

Usage: python -m seeds.seed_runner
"""

import logging
import os
import sys

from sqlmodel import Session, select

from app.db.database import engine
from app.models.user import User
from app.models.password_reset import PasswordReset  # noqa: F401 — needed for SQLAlchemy relationship resolution
from seeds.data.users import get_users

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _guard_environment():
    app_env = os.getenv("APP_ENV", "development")
    if app_env != "development":
        logger.info(f"Skipping seed in APP_ENV={app_env}")
        sys.exit(0)


def seed_users(session: Session) -> None:
    users_data = get_users()
    created = 0
    updated = 0

    for data in users_data:
        existing = session.exec(select(User).where(User.email == data["email"])).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            session.add(existing)
            updated += 1
        else:
            user = User(**data)
            session.add(user)
            created += 1

    session.commit()
    logger.info(f"Users: {created} created, {updated} updated")


def run():
    _guard_environment()
    logger.info("Seeding database...")

    with Session(engine) as session:
        seed_users(session)

    logger.info("Seeding complete.")


if __name__ == "__main__":
    run()
