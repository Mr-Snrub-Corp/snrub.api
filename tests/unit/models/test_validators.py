from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.incident_report import IncidentReportCreateRequest, IncidentReportUpdateRequest
from app.models.incident_type import IncidentTypeCreateRequest, IncidentTypeUpdateRequest
from app.models.validators import validate_ines_severity, validate_ines_severity_optional


class TestValidateInesSeverity:
    @pytest.mark.parametrize("v", [1, 2, 3, 4, 5, 6, 7])
    def test_accepts_full_ines_scale(self, v: int):
        assert validate_ines_severity(v) == v

    @pytest.mark.parametrize("v", [0, 8, -1, 100])
    def test_rejects_out_of_range(self, v: int):
        with pytest.raises(ValueError, match="1-7 .INES scale."):
            validate_ines_severity(v)


class TestValidateInesSeverityOptional:
    def test_passes_none_through(self):
        assert validate_ines_severity_optional(None) is None

    @pytest.mark.parametrize("v", [1, 4, 7])
    def test_accepts_in_range(self, v: int):
        assert validate_ines_severity_optional(v) == v

    @pytest.mark.parametrize("v", [0, 8, -1])
    def test_rejects_out_of_range(self, v: int):
        with pytest.raises(ValueError, match="1-7 .INES scale."):
            validate_ines_severity_optional(v)


class TestIncidentReportWiring:
    """The shared validators are actually attached to the request models."""

    def _create(self, severity: int) -> IncidentReportCreateRequest:
        return IncidentReportCreateRequest(
            incident_type_id=uuid4(),
            severity=severity,
            occurred_at=datetime(2026, 1, 1),
        )

    def test_create_accepts_valid_severity(self):
        assert self._create(4).severity == 4

    def test_create_rejects_out_of_range(self):
        with pytest.raises(ValidationError, match="INES scale"):
            self._create(9)

    def test_update_allows_omitting_severity(self):
        assert IncidentReportUpdateRequest().severity is None

    def test_update_rejects_out_of_range(self):
        with pytest.raises(ValidationError, match="INES scale"):
            IncidentReportUpdateRequest(severity=0)


class TestIncidentTypeWiring:
    """Mirror of TestIncidentReportWiring for the incident-type request models."""

    def _create(self, severity: int) -> IncidentTypeCreateRequest:
        return IncidentTypeCreateRequest(
            code="cooling_tower_failure",
            name="Meh",
            category_id=uuid4(),
            default_severity=severity,
        )

    def test_create_accepts_valid_severity(self):
        assert self._create(4).default_severity == 4

    def test_create_rejects_out_of_range(self):
        with pytest.raises(ValidationError, match="INES scale"):
            self._create(9)

    def test_update_allows_omitting_severity(self):
        assert IncidentTypeUpdateRequest().default_severity is None

    def test_update_rejects_out_of_range(self):
        with pytest.raises(ValidationError, match="INES scale"):
            IncidentTypeUpdateRequest(default_severity=0)
