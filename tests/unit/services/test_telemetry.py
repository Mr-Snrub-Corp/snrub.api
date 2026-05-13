from unittest.mock import patch

from app.services.telemetry import noise


class TestNoise:
    def test_non_zero_value_is_multiplied(self):
        with patch("app.services.telemetry.random.uniform", return_value=1.002):
            result = noise({"reactor_power": 100.0})

        assert result["reactor_power"] == 100.0 * 1.002

    def test_zero_value_is_incremented(self):
        """Zero values take the additive branch (reactivity starts at 0)."""
        with patch("app.services.telemetry.random.uniform", return_value=1.002):
            result = noise({"reactivity": 0.0})

        assert result["reactivity"] == 0.0 + 1.002

    def test_all_input_keys_present_in_output(self):
        data = {"reactor_power": 95.0, "core_temperature": 700.0, "reactivity": 0.0}

        result = noise(data)

        assert set(result.keys()) == set(data.keys())

    def test_no_extra_keys_in_output(self):
        data = {"reactor_power": 95.0}

        result = noise(data)

        assert list(result.keys()) == ["reactor_power"]

    def test_original_dict_is_not_mutated(self):
        data = {"reactor_power": 95.0, "reactivity": 0.0}
        original = dict(data)

        noise(data)

        assert data == original

    def test_empty_dict_returns_empty_dict(self):
        assert noise({}) == {}
