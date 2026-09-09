"""Persisted plant simulation snapshot (Phase 3, docs/roadmap.md).

One continuously-upserted row: the simulator process writes the integrated
true physical state and the measured sensor readings every tick; request
handlers stay stateless and read the latest row. Both are stored because
sensor lag/health is stateful — sampling per API request would fork sensor
state per client, and the persisted measured values double as the lag-filter
state across simulator restarts.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger
from sqlmodel import Field, SQLModel

# Canonical metric keys, mirrored by the true_*/measured_* column pairs below.
_METRICS = (
    "reactor_power",
    "core_temperature",
    "reactivity",
    "coolant_flow_rate",
    "coolant_pressure",
    "radiation_level",
    "containment_integrity",
)


class PlantStateBase(SQLModel, table=False):
    tick: int = Field(default=0, sa_type=BigInteger)

    true_reactor_power: float
    true_core_temperature: float
    true_reactivity: float
    true_coolant_flow_rate: float
    true_coolant_pressure: float
    true_radiation_level: float
    true_containment_integrity: float

    measured_reactor_power: float
    measured_core_temperature: float
    measured_reactivity: float
    measured_coolant_flow_rate: float
    measured_coolant_pressure: float
    measured_radiation_level: float
    measured_containment_integrity: float


class PlantState(PlantStateBase, table=True):
    __tablename__ = "plant_states"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class PlantStateResponse(PlantStateBase):
    uid: UUID
    created: datetime
    updated: datetime


def true_state_dict(row: PlantStateBase) -> dict[str, float]:
    """True physical state keyed by canonical metric name."""
    return {metric: getattr(row, f"true_{metric}") for metric in _METRICS}


def measured_dict(row: PlantStateBase) -> dict[str, float]:
    """Measured sensor readings keyed by canonical metric name."""
    return {metric: getattr(row, f"measured_{metric}") for metric in _METRICS}
