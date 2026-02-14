"""Database seed runner. Only runs in development.

Usage: python -m seeds.seed_runner
"""

import logging
import os
import sys
from datetime import datetime

from sqlmodel import Session, select

from app.db.database import engine
from app.models.incident_category import IncidentCategory
from app.models.incident_report import IncidentReport
from app.models.incident_report_subject import IncidentReportSubject
from app.models.incident_type import IncidentType
from app.models.password_reset import PasswordReset  # noqa: F401 — needed for SQLAlchemy relationship resolution
from app.models.user import User
from seeds.data.incident_categories import INCIDENT_CATEGORIES
from seeds.data.incident_reports import INCIDENT_REPORTS
from seeds.data.incident_types import INCIDENT_TYPES
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


def seed_incident_categories(session: Session) -> None:
    created = 0
    updated = 0

    for data in INCIDENT_CATEGORIES:
        existing = session.exec(select(IncidentCategory).where(IncidentCategory.code == data["code"])).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            session.add(existing)
            updated += 1
        else:
            category = IncidentCategory(**data)
            session.add(category)
            created += 1

    session.commit()
    logger.info(f"Incident categories: {created} created, {updated} updated")


def seed_incident_types(session: Session) -> None:
    # Build category code -> uid lookup
    categories = session.exec(select(IncidentCategory)).all()
    cat_lookup = {c.code: c.uid for c in categories}

    created = 0
    updated = 0

    for data in INCIDENT_TYPES:
        entry = {k: v for k, v in data.items() if k != "category_code"}
        entry["category_id"] = cat_lookup[data["category_code"]]

        existing = session.exec(select(IncidentType).where(IncidentType.code == entry["code"])).first()
        if existing:
            for key, value in entry.items():
                setattr(existing, key, value)
            session.add(existing)
            updated += 1
        else:
            session.add(IncidentType(**entry))
            created += 1

    session.commit()
    logger.info(f"Incident types: {created} created, {updated} updated")


def seed_incident_reports(session: Session) -> None:
    # Build lookups
    users = session.exec(select(User)).all()
    user_lookup = {u.email: u.uid for u in users}

    types = session.exec(select(IncidentType)).all()
    type_lookup = {t.code: t.uid for t in types}

    created = 0
    updated = 0

    for data in INCIDENT_REPORTS:
        entry = {k: v for k, v in data.items() if k not in ("incident_type_code", "reported_by_email", "subjects")}
        entry["incident_type_id"] = type_lookup[data["incident_type_code"]]
        entry["reported_by_user_id"] = user_lookup[data["reported_by_email"]]
        entry["occurred_at"] = datetime.fromisoformat(data["occurred_at"])

        # Upsert by composite key
        existing = session.exec(
            select(IncidentReport).where(
                IncidentReport.incident_type_id == entry["incident_type_id"],
                IncidentReport.occurred_at == entry["occurred_at"],
                IncidentReport.reported_by_user_id == entry["reported_by_user_id"],
            )
        ).first()

        if existing:
            for key, value in entry.items():
                setattr(existing, key, value)
            session.add(existing)
            report_uid = existing.uid
            updated += 1
        else:
            report = IncidentReport(**entry)
            session.add(report)
            session.flush()
            report_uid = report.uid
            created += 1

        # Delete + recreate subjects
        old_subjects = session.exec(
            select(IncidentReportSubject).where(IncidentReportSubject.incident_report_id == report_uid)
        ).all()
        for s in old_subjects:
            session.delete(s)

        for s_data in data.get("subjects", []):
            subject = IncidentReportSubject(
                incident_report_id=report_uid,
                user_id=user_lookup[s_data["user_email"]],
                role=s_data["role"],
            )
            session.add(subject)

    session.commit()
    logger.info(f"Incident reports: {created} created, {updated} updated")


def run():
    _guard_environment()
    logger.info("Seeding database...")

    with Session(engine) as session:
        seed_users(session)
        seed_incident_categories(session)
        seed_incident_types(session)
        seed_incident_reports(session)

    logger.info("Seeding complete.")


if __name__ == "__main__":
    run()
