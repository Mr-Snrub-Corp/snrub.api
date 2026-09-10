from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from app.controllers.incident_report import get_reports_for_telemetry
from app.controllers.telemetry import get_reactor_metrics
from app.models.incident_report import EscalationLevel, IncidentReport, IncidentStatus
from app.models.incident_type import IncidentType
from app.models.plant_state import PlantState
from app.services.plant_model import METRICS
from app.services.telemetry import BASE_METRICS

ACTIVE_STATUSES = ["reported", "under_review", "confirmed", "mitigation_in_progress"]
TRACKED_CODE = "primary_coolant_loss"


def _plant_state(**measured) -> PlantState:
    """A PlantState row: true_* at base, measured_* overridable per metric."""
    values = {}
    for metric in METRICS:
        values[f"true_{metric}"] = BASE_METRICS[metric]
        values[f"measured_{metric}"] = measured.get(metric, BASE_METRICS[metric])
    return PlantState(**values)


def _clear_plant_states(session):
    """Drop any row a running simulator committed to the shared dev DB.

    The session fixture's rollback restores it after the test, so the two
    processes don't interfere.
    """
    for row in session.exec(select(PlantState)).all():
        session.delete(row)
    session.flush()


@pytest.fixture
def tracked_type(session, sample_category):
    existing = session.exec(select(IncidentType).where(IncidentType.code == TRACKED_CODE)).first()
    if existing:
        return existing
    t = IncidentType(
        code=TRACKED_CODE,
        name="Primary Coolant Loss",
        category_id=sample_category.uid,
        default_severity=5,
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


# _make_report is a module-level helper (not a fixture)
# so it can be called multiple times within a single test with different args.
def _make_report(session, incident_type, user, status=IncidentStatus.REPORTED, occurred_at=None):
    report = IncidentReport(
        incident_type_id=incident_type.uid,
        severity=4,
        status=status,
        escalation_level=EscalationLevel.NONE,
        reported_by_user_id=user.uid,
        occurred_at=occurred_at or datetime.utcnow(),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


class TestGetReportsForTelemetry:
    def test_returns_matching_report(self, session, tracked_type, creator_user):
        _make_report(session, tracked_type, creator_user)

        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert len(result) == 1
        assert result[0].incident_type_code == TRACKED_CODE
        assert result[0].status == IncidentStatus.REPORTED

    def test_returns_empty_when_no_reports(self, session):
        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert result == []

    def test_multiple_reports_all_returned(self, session, tracked_type, creator_user):
        _make_report(session, tracked_type, creator_user)
        _make_report(session, tracked_type, creator_user, status=IncidentStatus.CONFIRMED)

        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert len(result) == 2

    def test_excludes_inactive_status(self, session, tracked_type, creator_user):
        _make_report(session, tracked_type, creator_user, status=IncidentStatus.RESOLVED)

        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert result == []

    def test_excludes_untracked_incident_type(self, session, sample_type, creator_user):
        # sample_type has a random code not in the tracked list
        _make_report(session, sample_type, creator_user)

        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert result == []

    def test_excludes_report_before_date_from(self, session, tracked_type, creator_user):
        two_weeks_ago = datetime.utcnow() - timedelta(weeks=2)
        _make_report(session, tracked_type, creator_user, occurred_at=two_weeks_ago)

        result = get_reports_for_telemetry(session, ACTIVE_STATUSES, [TRACKED_CODE])

        assert result == []

    def test_excludes_report_after_date_to(self, session, tracked_type, creator_user):
        future = datetime.utcnow() + timedelta(days=2)
        _make_report(session, tracked_type, creator_user, occurred_at=future)

        result = get_reports_for_telemetry(
            session,
            ACTIVE_STATUSES,
            [TRACKED_CODE],
            date_to=datetime.utcnow(),
        )

        assert result == []

    def test_explicit_date_range_respected(self, session, tracked_type, creator_user):
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        _make_report(session, tracked_type, creator_user, occurred_at=three_days_ago)

        result = get_reports_for_telemetry(
            session,
            ACTIVE_STATUSES,
            [TRACKED_CODE],
            date_from=datetime.utcnow() - timedelta(weeks=1),
            date_to=datetime.utcnow(),
        )

        assert len(result) == 1


class TestGetReactorMetrics:
    def test_no_snapshot_returns_base_metrics(self, session):
        _clear_plant_states(session)

        result = get_reactor_metrics(session)

        assert result == BASE_METRICS

    def test_returns_measured_values_from_snapshot(self, session):
        _clear_plant_states(session)
        session.add(_plant_state(core_temperature=1042.0, coolant_flow_rate=48.0))
        session.flush()

        result = get_reactor_metrics(session)

        assert result["core_temperature"] == 1042.0
        assert result["coolant_flow_rate"] == 48.0
        assert set(result.keys()) == set(METRICS)

    def test_serves_measured_not_true_state(self, session):
        # true_* at base, measured_* elevated: the reader returns what the sensors saw.
        _clear_plant_states(session)
        session.add(_plant_state(radiation_level=75.0))
        session.flush()

        assert get_reactor_metrics(session)["radiation_level"] == 75.0

    def test_newest_updated_row_wins(self, session):
        _clear_plant_states(session)
        older = _plant_state(core_temperature=800.0)
        older.updated = datetime.utcnow() - timedelta(seconds=30)
        newer = _plant_state(core_temperature=950.0)
        newer.updated = datetime.utcnow()
        session.add(older)
        session.add(newer)
        session.flush()

        assert get_reactor_metrics(session)["core_temperature"] == 950.0
