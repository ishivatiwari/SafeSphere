"""Integration and endpoint tests for the SafeSphere API.

Covers:
- /health endpoint correctness
- /analyze: happy-path, caching, error paths
- Security headers on all responses
- Input validation (boundary values, edge cases)
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Stub out Google Cloud SDKs before importing app ──────────────────────────
_mock_firestore = MagicMock()
_mock_logging = MagicMock()

sys.modules.setdefault("google.cloud.logging", _mock_logging)
sys.modules.setdefault("google.cloud.logging.handlers", _mock_logging)
sys.modules.setdefault("google.cloud.firestore", _mock_firestore)

# Patch at module level so startup code sees the stubs
with patch("google.cloud.logging.Client", MagicMock()):
    from main import app, _analysis_cache  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# ── Shared fixtures & test data ─────────────────────────────────────────────

VALID_PAYLOAD = [
    {"zone_id": "A1", "density": 85, "movement_speed": 1.2},
    {"zone_id": "B2", "density": 95, "movement_speed": 0.5},
]

MOCK_GEMINI_RESPONSE = {
    "zone_status": [
        {
            "zone_id": "A1",
            "density_level": "High",
            "risk_level": "High Risk",
            "trend": "Increasing",
        },
        {
            "zone_id": "B2",
            "density_level": "Critical",
            "risk_level": "Stampede Risk",
            "trend": "Increasing",
        },
    ],
    "actions": ["Redirect crowd from B2 to safe exit", "Open alternate gate"],
    "alerts": ["Critical density in zone B2 — immediate action required"],
}


class _FakeGeminiResponse:
    """Minimal stand-in for the google-genai response object."""

    def __init__(self, payload: dict = None):
        self.text = json.dumps(payload or MOCK_GEMINI_RESPONSE)


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure each test starts with an empty TTL cache."""
    _analysis_cache.clear()
    yield
    _analysis_cache.clear()


@pytest.fixture
def mock_gemini(monkeypatch):
    """Provide a pre-configured mock Gemini client injected into the app."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc123")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _FakeGeminiResponse()
    with patch("main._gemini_client", mock_client), patch(
        "main.get_gemini_client", return_value=mock_client
    ):
        yield mock_client


# ── /health ──────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self):
        assert client.get("/health").status_code == 200

    def test_status_is_healthy(self):
        assert client.get("/health").json()["status"] == "healthy"

    def test_version_present(self):
        assert "version" in client.get("/health").json()

    def test_services_block_present(self):
        assert "services" in client.get("/health").json()

    def test_services_contains_firestore_key(self):
        assert "firestore" in client.get("/health").json()["services"]

    def test_services_contains_cache_size(self):
        assert "cache_size" in client.get("/health").json()["services"]


# ── /analyze — happy paths ─────────────────────────────────────────────────

class TestAnalyzeEndpoint:
    def test_valid_request_returns_200(self, mock_gemini):
        assert client.post("/analyze", json=VALID_PAYLOAD).status_code == 200

    def test_response_has_zone_status(self, mock_gemini):
        data = client.post("/analyze", json=VALID_PAYLOAD).json()
        assert "zone_status" in data
        assert len(data["zone_status"]) == 2

    def test_response_has_actions_list(self, mock_gemini):
        data = client.post("/analyze", json=VALID_PAYLOAD).json()
        assert isinstance(data["actions"], list)

    def test_response_has_alerts_list(self, mock_gemini):
        data = client.post("/analyze", json=VALID_PAYLOAD).json()
        assert isinstance(data["alerts"], list)

    def test_zone_status_all_fields_present(self, mock_gemini):
        zone = client.post("/analyze", json=VALID_PAYLOAD).json()["zone_status"][0]
        for field in ("zone_id", "density_level", "risk_level", "trend"):
            assert field in zone, f"Missing field: {field}"

    def test_single_zone_request(self, mock_gemini):
        single_zone_response = {
            "zone_status": [
                {
                    "zone_id": "C3",
                    "density_level": "Medium",
                    "risk_level": "Low Risk",
                    "trend": "Stable",
                }
            ],
            "actions": ["Monitor zone C3"],
            "alerts": [],
        }
        mock_gemini.models.generate_content.return_value = _FakeGeminiResponse(
            single_zone_response
        )
        payload = [{"zone_id": "C3", "density": 50, "movement_speed": 2.0}]
        assert client.post("/analyze", json=payload).status_code == 200

    def test_critical_zone_triggers_alert(self, mock_gemini):
        data = client.post("/analyze", json=VALID_PAYLOAD).json()
        assert len(data["alerts"]) > 0

    def test_caching_prevents_duplicate_gemini_calls(self, mock_gemini):
        client.post("/analyze", json=VALID_PAYLOAD)
        client.post("/analyze", json=VALID_PAYLOAD)
        assert mock_gemini.models.generate_content.call_count == 1

    def test_different_payloads_bypass_cache(self, mock_gemini):
        client.post("/analyze", json=VALID_PAYLOAD)
        different = [{"zone_id": "Z9", "density": 10, "movement_speed": 3.0}]
        mock_gemini.models.generate_content.return_value = _FakeGeminiResponse(
            {
                "zone_status": [
                    {
                        "zone_id": "Z9",
                        "density_level": "Low",
                        "risk_level": "Low Risk",
                        "trend": "Stable",
                    }
                ],
                "actions": [],
                "alerts": [],
            }
        )
        client.post("/analyze", json=different)
        assert mock_gemini.models.generate_content.call_count == 2


# ── /analyze — error paths ────────────────────────────────────────────────────

class TestAnalyzeErrorPaths:
    def test_empty_list_returns_422(self, mock_gemini):
        assert client.post("/analyze", json=[]).status_code == 422

    def test_missing_api_key_returns_500(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with patch("main._gemini_client", None):
            resp = client.post("/analyze", json=VALID_PAYLOAD)
        assert resp.status_code == 500

    def test_gemini_exception_returns_500(self, mock_gemini):
        mock_gemini.models.generate_content.side_effect = RuntimeError("API timeout")
        resp = client.post("/analyze", json=VALID_PAYLOAD)
        assert resp.status_code == 500

    def test_not_a_list_returns_422(self, mock_gemini):
        payload = {"zone_id": "A1", "density": 50, "movement_speed": 1.0}
        assert client.post("/analyze", json=payload).status_code == 422


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_density_above_200_rejected(self):
        payload = [{"zone_id": "X1", "density": 201, "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_density_below_0_rejected(self):
        payload = [{"zone_id": "X1", "density": -1, "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_negative_speed_rejected(self):
        payload = [{"zone_id": "X1", "density": 50, "movement_speed": -0.1}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_empty_zone_id_rejected(self):
        payload = [{"zone_id": "", "density": 50, "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_zone_id_over_20_chars_rejected(self):
        payload = [{"zone_id": "A" * 21, "density": 50, "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_missing_density_rejected(self):
        payload = [{"zone_id": "A1", "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_missing_speed_rejected(self):
        payload = [{"zone_id": "A1", "density": 50}]
        assert client.post("/analyze", json=payload).status_code == 422

    def test_boundary_density_zero_accepted(self, mock_gemini):
        mock_gemini.models.generate_content.return_value = _FakeGeminiResponse(
            {
                "zone_status": [
                    {
                        "zone_id": "A1",
                        "density_level": "Low",
                        "risk_level": "Low Risk",
                        "trend": "Stable",
                    }
                ],
                "actions": [],
                "alerts": [],
            }
        )
        payload = [{"zone_id": "A1", "density": 0, "movement_speed": 1.0}]
        assert client.post("/analyze", json=payload).status_code == 200

    def test_boundary_density_200_accepted(self, mock_gemini):
        mock_gemini.models.generate_content.return_value = _FakeGeminiResponse(
            {
                "zone_status": [
                    {
                        "zone_id": "A1",
                        "density_level": "Critical",
                        "risk_level": "Stampede Risk",
                        "trend": "Increasing",
                    }
                ],
                "actions": ["Evacuate immediately"],
                "alerts": ["CRITICAL: Zone A1"],
            }
        )
        payload = [{"zone_id": "A1", "density": 200, "movement_speed": 0.0}]
        assert client.post("/analyze", json=payload).status_code == 200

    def test_speed_boundary_zero_accepted(self, mock_gemini):
        mock_gemini.models.generate_content.return_value = _FakeGeminiResponse(
            {
                "zone_status": [
                    {
                        "zone_id": "A1",
                        "density_level": "High",
                        "risk_level": "High Risk",
                        "trend": "Increasing",
                    }
                ],
                "actions": [],
                "alerts": [],
            }
        )
        payload = [{"zone_id": "A1", "density": 80, "movement_speed": 0}]
        assert client.post("/analyze", json=payload).status_code == 200


# ── Security headers ──────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_x_content_type_options(self):
        assert client.get("/health").headers["x-content-type-options"] == "nosniff"

    def test_x_frame_options(self):
        assert client.get("/health").headers["x-frame-options"] == "DENY"

    def test_x_xss_protection(self):
        assert client.get("/health").headers["x-xss-protection"] == "1; mode=block"

    def test_referrer_policy(self):
        assert (
            client.get("/health").headers["referrer-policy"]
            == "strict-origin-when-cross-origin"
        )

    def test_security_headers_on_analyze(self, mock_gemini):
        resp = client.post("/analyze", json=VALID_PAYLOAD)
        assert resp.headers.get("x-frame-options") == "DENY"
