from sqlmodel import Session

from app.controllers.incident_report import get_reports
from app.services.telemetry import TRACKED_INCIDENT_TYPE_CODES, compute_metrics


# class IncidentStatus(StrEnum):
#     REPORTED = "reported"
#     UNDER_REVIEW = "under_review"
#     CONFIRMED = "confirmed"
#     FALSE_ALARM = "false_alarm"
#     CONTAINED = "contained"
#     MITIGATION_IN_PROGRESS = "mitigation_in_progress"
#     RESOLVED = "resolved"
#     CLOSED = "closed"


def get_reactor_metrics(session: Session):
    reports = get_reports(
        session,
        0,
        20,
        ["reported", "under_review", "confirmed", "mitigation_in_progress"],
        TRACKED_INCIDENT_TYPE_CODES,
    )
    # need to filter incident_types eg operator asleep doesn't matter
    metrics = compute_metrics(reports)
    return metrics
