"""Phase 4 incident_emitter: DANGER → debounced auto-incident.

Classify + debounce are pure (no DB). Dedup lives in file_auto_reports and is
covered by the integration suite — these tests prove the tick logic that
feeds it: sustained DANGER becomes ready, WARNING/normal never do, recovery
resets the streak, and ready stays ready until the excursion ends.
"""

from app.services.incident_emitter import DEBOUNCE_TICKS, current_excursions, update_streaks
from app.services.telemetry import BASE_METRICS


def _state(**overrides: float) -> dict[str, float]:
    return {**BASE_METRICS, **overrides}


class TestCurrentExcursions:
    def test_normal_state_is_empty(self):
        assert current_excursions(_state()) == {}

    def test_warning_is_not_an_excursion(self):
        # core_temperature warning starts at 900; danger at 1000.
        assert current_excursions(_state(core_temperature=950)) == {}

    def test_danger_high_maps_to_code(self):
        assert current_excursions(_state(core_temperature=1000)) == {
            "core_temperature": "coolant_temperature_exceedance"
        }

    def test_danger_low_maps_to_code(self):
        assert current_excursions(_state(coolant_flow_rate=20)) == {"coolant_flow_rate": "coolant_flow_reduction"}

    def test_reactivity_high_is_excursion_risk(self):
        assert current_excursions(_state(reactivity=3)) == {"reactivity": "reactivity_excursion_risk"}

    def test_unknown_metric_is_skipped(self):
        assert current_excursions(_state(not_a_metric=999)) == {}


class TestUpdateStreaks:
    def test_normal_tick_emits_nothing_and_clears_streaks(self):
        next_streaks, ready = update_streaks({"coolant_flow_rate": 2}, {})
        assert next_streaks == {}
        assert ready == []

    def test_transient_danger_is_not_ready(self):
        excursions = {"coolant_flow_rate": "coolant_flow_reduction"}
        next_streaks, ready = update_streaks({}, excursions)
        assert next_streaks == {"coolant_flow_rate": 1}
        assert ready == []
        assert DEBOUNCE_TICKS > 1

    def test_sustained_danger_becomes_ready(self):
        excursions = {"coolant_flow_rate": "coolant_flow_reduction"}
        streaks: dict[str, int] = {}
        ready: list[str] = []
        for _ in range(DEBOUNCE_TICKS):
            streaks, ready = update_streaks(streaks, excursions)
        assert ready == ["coolant_flow_reduction"]
        assert streaks["coolant_flow_rate"] == DEBOUNCE_TICKS

    def test_ready_repeats_each_tick_until_recovery(self):
        """Dedup is the emit layer's job; debounce keeps signalling while DANGER holds."""
        excursions = {"coolant_flow_rate": "coolant_flow_reduction"}
        streaks: dict[str, int] = {}
        for _ in range(DEBOUNCE_TICKS):
            streaks, ready = update_streaks(streaks, excursions)
        _, ready_again = update_streaks(streaks, excursions)
        assert ready_again == ["coolant_flow_reduction"]

    def test_recovery_resets_streak(self):
        excursions = {"coolant_flow_rate": "coolant_flow_reduction"}
        streaks: dict[str, int] = {}
        for _ in range(DEBOUNCE_TICKS):
            streaks, _ = update_streaks(streaks, excursions)
        streaks, ready = update_streaks(streaks, {})
        assert streaks == {}
        assert ready == []
        # A new excursion must debounce again (not inherit the old streak).
        streaks, ready = update_streaks(streaks, excursions)
        assert ready == []
        assert streaks == {"coolant_flow_rate": 1}
