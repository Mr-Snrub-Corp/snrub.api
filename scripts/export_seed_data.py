"""Export dev DB data to seed-friendly format.

Usage: docker compose exec api python scripts/export_seed_data.py
"""

import sys
from pathlib import Path

from sqlmodel import Session, select

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import engine  # noqa: E402
from app.models.incident_category import IncidentCategory  # noqa: E402
from app.models.incident_report import IncidentReport  # noqa: E402
from app.models.incident_report_subject import IncidentReportSubject  # noqa: E402
from app.models.incident_type import IncidentType  # noqa: E402
from app.models.password_reset import PasswordReset  # noqa: E402, F401
from app.models.user import User  # noqa: E402
from seeds.data.users import USERS  # noqa: E402

PHOTOS_DIR = Path(__file__).resolve().parent.parent / "seeds" / "data" / "photos"

EXISTING_EMAILS = {u["email"] for u in USERS}


def export_new_users(session: Session):
    users = session.exec(select(User).order_by(User.name)).all()
    new_users = [u for u in users if u.email not in EXISTING_EMAILS]

    if not new_users:
        print("\n# No new users found")
        return

    print("\n# === NEW USERS (append to seeds/data/users.py USERS list) ===")
    for u in new_users:
        # Write photo
        photo_filename = u.email.split("@")[0].replace(".", "_") + ".png"
        if u.photo:
            photo_path = PHOTOS_DIR / photo_filename
            photo_path.write_bytes(u.photo)
            print(f"# Photo written: {photo_path.name}")

        print("    {")
        print(f'        "email": "{u.email}",')
        print(f'        "name": "{u.name}",')
        print(f'        "role": UserRole.{u.role.name},')
        print(f'        "status": UserStatus.{u.status.name},')
        print(f'        "photo_file": "{photo_filename}",')
        print("    },")


def export_incident_reports(session: Session):
    # Build lookups
    types = session.exec(select(IncidentType)).all()
    type_lookup = {t.uid: t.code for t in types}

    users = session.exec(select(User)).all()
    user_lookup = {u.uid: u.email for u in users}

    reports = session.exec(select(IncidentReport).order_by(IncidentReport.occurred_at)).all()

    if not reports:
        print("\n# No incident reports found")
        return

    print("\n# === INCIDENT_REPORTS (for seeds/data/incident_reports.py) ===")
    print("from app.models.incident_report import EscalationLevel, IncidentStatus")
    print("from app.models.incident_report_subject import SubjectRole")
    print("")
    print("INCIDENT_REPORTS = [")

    for report in reports:
        subjects = session.exec(
            select(IncidentReportSubject).where(IncidentReportSubject.incident_report_id == report.uid)
        ).all()

        print("    {")
        print(f'        "incident_type_code": "{type_lookup[report.incident_type_id]}",')
        print(f'        "reported_by_email": "{user_lookup[report.reported_by_user_id]}",')
        if report.description:
            desc = report.description.replace('"', '\\"')
            print(f'        "description": "{desc}",')
        else:
            print('        "description": None,')
        print(f'        "severity": {report.severity},')
        print(f'        "status": IncidentStatus.{report.status.name},')
        print(f'        "escalation_level": EscalationLevel.{report.escalation_level.name},')
        print(f'        "occurred_at": "{report.occurred_at.isoformat()}",')

        if subjects:
            print('        "subjects": [')
            for s in subjects:
                print(f'            {{"user_email": "{user_lookup[s.user_id]}", "role": SubjectRole.{s.role.name}}},')
            print("        ],")
        else:
            print('        "subjects": [],')

        print("    },")

    print("]")


def main():
    print("Exporting seed data from dev database...")
    with Session(engine) as session:
        export_new_users(session)
        export_incident_reports(session)
    print("\n# Export complete.")


if __name__ == "__main__":
    main()
