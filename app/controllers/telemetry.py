from sqlmodel import Session

from app.controllers.incident_report import get_reports_for_telemetry
from app.services.telemetry import TRACKED_INCIDENT_TYPE_CODES, compute_metrics


def get_reactor_metrics(session: Session):
    """Fetch recent active incident reports and compute live reactor metrics."""
    reports = get_reports_for_telemetry(
        session,
        ["reported", "under_review", "confirmed", "mitigation_in_progress"],
        TRACKED_INCIDENT_TYPE_CODES,
    )
    # need to filter incident_types eg operator asleep doesn't matter
    metrics = compute_metrics(reports)
    return metrics
