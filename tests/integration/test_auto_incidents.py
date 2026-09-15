"""Phase 4: a sustained DANGER excursion files exactly one [auto] incident."""

from sqlmodel import select

from app.controllers.incident_report import get_reports_for_telemetry
from app.core.config import settings
from app.models.incident_report import IncidentReport, IncidentStatus
from app.models.incident_type import IncidentType
from app.models.user import User
from app.services.incident_emitter import AUTO_MARKER, DEBOUNCE_TICKS, emit
from app.services.telemetry import ACTIVE_INCIDENT_STATUSES, BASE_METRICS


def _danger_flow() -> dict[str, float]:
    return {**BASE_METRICS, "coolant_flow_rate": 20.0}


def _ensure_type(session, sample_category, code: str) -> IncidentType:
    existing = session.exec(select(IncidentType).where(IncidentType.code == code)).first()
    if existing:
        return existing
    t = IncidentType(
        code=code,
        name=code.replace("_", " ").title(),
        category_id=sample_category.uid,
        default_severity=5,
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def _system_user(session) -> User:
    user = session.exec(select(User).where(User.email == settings.SYSTEM_USER_EMAIL)).first()
    assert user is not None, "system user seed missing — run alembic upgrade head"
    return user


class TestEmitExactlyOne:
    def test_sustained_danger_files_exactly_one_auto_report(self, session, sample_category):
        _ensure_type(session, sample_category, "coolant_flow_reduction")
        _system_user(session)
        streaks: dict[str, int] = {}

        for _ in range(DEBOUNCE_TICKS + 2):
            emit(_danger_flow(), streaks, session)

        reports = get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])
        assert len(reports) == 1
        assert reports[0].incident_type_code == "coolant_flow_reduction"

        row = session.exec(select(IncidentReport).where(IncidentReport.description.startswith(AUTO_MARKER))).first()
        assert row is not None
        assert row.status == IncidentStatus.REPORTED
        assert row.reported_by_user_id == _system_user(session).uid

    def test_already_open_auto_report_is_not_duplicated(self, session, sample_category):
        _ensure_type(session, sample_category, "coolant_flow_reduction")
        _system_user(session)
        streaks: dict[str, int] = {}
        for _ in range(DEBOUNCE_TICKS):
            emit(_danger_flow(), streaks, session)
        emit(_danger_flow(), streaks, session)
        emit(_danger_flow(), streaks, session)

        reports = get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])
        assert len(reports) == 1

    def test_normal_state_files_nothing(self, session, sample_category):
        _ensure_type(session, sample_category, "coolant_flow_reduction")
        _system_user(session)
        streaks: dict[str, int] = {}
        emit(dict(BASE_METRICS), streaks, session)
        reports = get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])
        assert reports == []

    def test_recovery_then_new_excursion_files_again_only_after_debounce(self, session, sample_category):
        _ensure_type(session, sample_category, "coolant_flow_reduction")
        _system_user(session)
        streaks: dict[str, int] = {}
        for _ in range(DEBOUNCE_TICKS):
            emit(_danger_flow(), streaks, session)
        assert len(get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])) == 1

        # Recover: streak clears. Close the open report so a genuine second excursion can file.
        open_report = session.exec(
            select(IncidentReport).where(IncidentReport.description.startswith(AUTO_MARKER))
        ).first()
        assert open_report is not None
        open_report.status = IncidentStatus.RESOLVED
        session.add(open_report)
        session.commit()

        emit(dict(BASE_METRICS), streaks, session)
        emit(_danger_flow(), streaks, session)
        still = get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])
        assert still == []

        for _ in range(DEBOUNCE_TICKS - 1):
            emit(_danger_flow(), streaks, session)
        reports = get_reports_for_telemetry(session, ACTIVE_INCIDENT_STATUSES, ["coolant_flow_reduction"])
        assert len(reports) == 1
