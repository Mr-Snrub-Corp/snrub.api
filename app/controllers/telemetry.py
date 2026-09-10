from logging import getLogger

from sqlmodel import Session, select

from app.models.plant_state import PlantState, measured_dict
from app.services.telemetry import BASE_METRICS

logger = getLogger(__name__)

_warned_no_snapshot = False


def get_reactor_metrics(session: Session) -> dict[str, float]:
    """Read the latest simulator snapshot; the measured sensor values are telemetry."""
    global _warned_no_snapshot
    row = session.exec(select(PlantState).order_by(PlantState.updated.desc())).first()
    if row is None:
        if not _warned_no_snapshot:
            logger.warning("No plant_states snapshot yet; serving base metrics (is the simulator running?)")
            _warned_no_snapshot = True
        return dict(BASE_METRICS)
    return measured_dict(row)
