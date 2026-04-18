"""Unit tests for SafeSphere Pydantic models.

Validates field constraints, boundary values, serialisation,
and cross-model composition independently of HTTP or Gemini.
"""

import pytest
from pydantic import ValidationError

# Stub cloud SDKs before importing from main
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("google.cloud.logging", MagicMock())
sys.modules.setdefault("google.cloud.logging.handlers", MagicMock())
sys.modules.setdefault("google.cloud.firestore", MagicMock())

from unittest.mock import patch

with patch("google.cloud.logging.Client", MagicMock()):
    from main import ZoneInput, ZoneStatus, SafeSphereOutput


# ── ZoneInput ─────────────────────────────────────────────────────────────────

class TestZoneInput:
    def test_valid_zone_input(self):
        z = ZoneInput(zone_id="A1", density=85.0, movement_speed=1.2)
        assert z.zone_id == "A1"
        assert z.density == 85.0
        assert z.movement_speed == 1.2

    # Density boundaries
    def test_density_boundary_zero(self):
        z = ZoneInput(zone_id="A1", density=0, movement_speed=1.0)
        assert z.density == 0

    def test_density_boundary_200(self):
        z = ZoneInput(zone_id="A1", density=200, movement_speed=1.0)
        assert z.density == 200

    def test_density_threshold_low_41(self):
        """41 is the boundary between Low and Medium density."""
        z = ZoneInput(zone_id="A1", density=41, movement_speed=1.0)
        assert z.density == 41

    def test_density_threshold_medium_70(self):
        z = ZoneInput(zone_id="A1", density=70, movement_speed=1.0)
        assert z.density == 70

    def test_density_threshold_high_71(self):
        z = ZoneInput(zone_id="A1", density=71, movement_speed=1.0)
        assert z.density == 71

    def test_density_threshold_critical_91(self):
        z = ZoneInput(zone_id="A1", density=91, movement_speed=1.0)
        assert z.density == 91

    def test_density_exceeds_max_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", density=201, movement_speed=1.0)

    def test_density_below_min_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", density=-1, movement_speed=1.0)

    # Speed boundaries
    def test_speed_boundary_zero(self):
        z = ZoneInput(zone_id="A1", density=50, movement_speed=0)
        assert z.movement_speed == 0

    def test_speed_boundary_max(self):
        z = ZoneInput(zone_id="A1", density=50, movement_speed=20)
        assert z.movement_speed == 20

    def test_speed_below_zero_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", density=50, movement_speed=-0.1)

    def test_speed_above_max_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", density=50, movement_speed=20.1)

    # Zone ID validation
    def test_empty_zone_id_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="", density=50, movement_speed=1.0)

    def test_zone_id_max_length_20(self):
        z = ZoneInput(zone_id="A" * 20, density=50, movement_speed=1.0)
        assert len(z.zone_id) == 20

    def test_zone_id_over_20_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A" * 21, density=50, movement_speed=1.0)

    def test_zone_id_length_1_accepted(self):
        z = ZoneInput(zone_id="Z", density=50, movement_speed=1.0)
        assert z.zone_id == "Z"

    # Serialisation
    def test_model_dump_keys(self):
        z = ZoneInput(zone_id="A1", density=85.0, movement_speed=1.2)
        d = z.model_dump()
        assert set(d.keys()) == {"zone_id", "density", "movement_speed"}

    def test_model_dump_values(self):
        z = ZoneInput(zone_id="A1", density=85.0, movement_speed=1.2)
        assert z.model_dump() == {"zone_id": "A1", "density": 85.0, "movement_speed": 1.2}

    # Missing required fields
    def test_missing_density_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", movement_speed=1.0)

    def test_missing_speed_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(zone_id="A1", density=50)

    def test_missing_zone_id_raises(self):
        with pytest.raises(ValidationError):
            ZoneInput(density=50, movement_speed=1.0)


# ── ZoneStatus ────────────────────────────────────────────────────────────────

class TestZoneStatus:
    def test_valid_zone_status(self):
        z = ZoneStatus(
            zone_id="A1",
            density_level="High",
            risk_level="High Risk",
            trend="Increasing",
        )
        assert z.zone_id == "A1"
        assert z.density_level == "High"
        assert z.risk_level == "High Risk"
        assert z.trend == "Increasing"

    def test_low_risk_zone_status(self):
        z = ZoneStatus(
            zone_id="Z1",
            density_level="Low",
            risk_level="Low Risk",
            trend="Stable",
        )
        assert z.risk_level == "Low Risk"

    def test_critical_zone_status(self):
        z = ZoneStatus(
            zone_id="B2",
            density_level="Critical",
            risk_level="Stampede Risk",
            trend="Increasing",
        )
        assert z.density_level == "Critical"

    def test_missing_trend_raises(self):
        with pytest.raises(ValidationError):
            ZoneStatus(zone_id="A1", density_level="High", risk_level="High Risk")

    def test_missing_risk_level_raises(self):
        with pytest.raises(ValidationError):
            ZoneStatus(zone_id="A1", density_level="High", trend="Stable")


# ── SafeSphereOutput ──────────────────────────────────────────────────────────

class TestSafeSphereOutput:
    def _make_zone(self, zone_id="A1", density="Low", risk="Low Risk", trend="Stable"):
        return ZoneStatus(
            zone_id=zone_id,
            density_level=density,
            risk_level=risk,
            trend=trend,
        )

    def test_valid_output(self):
        out = SafeSphereOutput(
            zone_status=[self._make_zone()],
            actions=["Monitor"],
            alerts=["Watch A1"],
        )
        assert len(out.zone_status) == 1

    def test_empty_alerts_valid(self):
        out = SafeSphereOutput(
            zone_status=[self._make_zone()],
            actions=["Monitor"],
            alerts=[],
        )
        assert out.alerts == []

    def test_empty_actions_valid(self):
        out = SafeSphereOutput(
            zone_status=[self._make_zone()],
            actions=[],
            alerts=[],
        )
        assert out.actions == []

    def test_multiple_zones(self):
        out = SafeSphereOutput(
            zone_status=[
                self._make_zone("A1"),
                self._make_zone("B2", "Critical", "Stampede Risk", "Increasing"),
                self._make_zone("C3", "Medium", "Low Risk", "Stable"),
            ],
            actions=["Evacuate B2"],
            alerts=["CRITICAL: B2"],
        )
        assert len(out.zone_status) == 3

    def test_model_validate_json(self):
        raw = (
            '{"zone_status": [{"zone_id": "A1", "density_level": "High", '
            '"risk_level": "High Risk", "trend": "Increasing"}], '
            '"actions": ["Redirect"], "alerts": ["Alert A1"]}'
        )
        out = SafeSphereOutput.model_validate_json(raw)
        assert out.zone_status[0].zone_id == "A1"
        assert out.actions == ["Redirect"]
        assert out.alerts == ["Alert A1"]

    def test_model_dump_structure(self):
        out = SafeSphereOutput(
            zone_status=[self._make_zone()],
            actions=["Act"],
            alerts=["Alert"],
        )
        d = out.model_dump()
        assert "zone_status" in d
        assert "actions" in d
        assert "alerts" in d

    def test_missing_zone_status_raises(self):
        with pytest.raises(ValidationError):
            SafeSphereOutput(actions=[], alerts=[])

    def test_missing_actions_raises(self):
        with pytest.raises(ValidationError):
            SafeSphereOutput(zone_status=[self._make_zone()], alerts=[])
