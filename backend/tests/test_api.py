"""API smoke tests for Progress-1."""

from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ai.services.expression_service import ExpressionRecognizer
from backend.app import main as main_module
from backend.app.core.database import engine
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def token(client):
    res = client.post(
        "/api/auth/login/json",
        json={"email": "caregiver@wellbeing.care", "password": "Caregiver123!"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    body = res.json()
    assert body["ready"] is True
    assert body["database_ready"] is True
    assert body["dependencies_ready"] is True
    assert body["ai_runtime_status"] in {"not_initialized", "demo_ready"}
    assert set(body["checks"]) == {"database", "dependencies", "ai"}
    assert body["checks"]["ai"]["model_revision"] == "747cf16692eea925b54b7b543cf436848128b68d"
    assert engine.url.database
    assert engine.url.database.endswith("test.db")


def test_health_returns_503_when_database_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_database_health",
        lambda: {"ready": False, "driver": "sqlite", "error": "OperationalError"},
    )
    res = client.get("/api/health")
    assert res.status_code == 503
    assert res.json()["status"] == "error"
    assert res.json()["ready"] is False
    assert res.json()["database_ready"] is False


def test_cors_uses_configured_local_origins(client):
    allowed = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

    blocked = client.options(
        "/api/health",
        headers={
            "Origin": "http://malicious.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert blocked.status_code == 400
    assert "access-control-allow-origin" not in blocked.headers


def test_login_and_dashboard(client, token):
    res = client.get("/api/dashboard/stats", headers=auth(token))
    assert res.status_code == 200
    body = res.json()
    assert "total_elderly_profiles" in body
    assert "disclaimer" in body


def test_session_predict_save(client, token):
    profiles = client.get("/api/elderly", headers=auth(token)).json()
    assert profiles
    elderly_id = profiles[0]["id"]
    sess = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": elderly_id},
    )
    assert sess.status_code == 200
    session_id = sess.json()["session_id"]

    tiny = (
        "data:image/jpeg;base64,"
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx"
        "NDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
        "MjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8Q"
        "AFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGcP//EABQQAQAAAAAAAAAAAAA"
        "AAAAAAAAT/9oACAEBAAEFAl//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/AX//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oA"
        "CAIBAQE/AX//xAAUEAEAAAAAAAAAAAAAAAAAAAAg/9oACAEBAAY/An//xAAUEAEAAAAAAAAAAAAAAAAAAAAg/9oACAEBAAE/IX//2g"
        "AMAwEAAgADAAAAEP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Qf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8"
        "Qf//Z"
    )
    pred = client.post(
        "/api/monitoring/predict",
        headers=auth(token),
        json={"image_base64": tiny, "session_id": session_id},
    )
    assert pred.status_code == 200
    body = pred.json()
    assert "expression" in body
    assert "confidence" in body
    assert "session_id" in body

    obs = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={
            "session_id": session_id,
            "elderly_id": elderly_id,
            "expression": "happy",
            "confidence": 0.91,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert obs.status_code == 201
    listed = client.get("/api/monitoring/observations", headers=auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_real_mode_returns_clear_ai_error_without_fake_prediction():
    recognizer = ExpressionRecognizer(demo_mode=True)
    recognizer.demo_mode = False
    recognizer._pipeline = None
    recognizer._cv2 = type(
        "CVStub",
        (),
        {
            "IMREAD_COLOR": 1,
            "cvtColor": staticmethod(lambda image, code: image),
            "imdecode": staticmethod(lambda data, flag: np.zeros((120, 120, 3), dtype=np.uint8)),
        },
    )()

    def fake_faces(_image):
        return [(0, 0, 120, 120)]

    recognizer.detect_faces = fake_faces

    result = recognizer.predict(
        "data:image/jpeg;base64,AAAA",
        "session-real-ai-error",
    )

    assert result["demo_mode"] is False
    assert result["expression"] == "unknown"
    assert result["confidence"] == 0.0
    assert "AI model unavailable" in result["message"] or "AI prediction failed" in result["message"]
    assert "fake" not in result["message"].lower()


def test_stopped_session_rejects_prediction_and_observation(client, token):
    profiles = client.get("/api/elderly", headers=auth(token)).json()
    session = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profiles[0]["id"]},
    ).json()
    session_id = session["session_id"]
    stopped = client.post(f"/api/monitoring/sessions/{session_id}/stop", headers=auth(token))
    assert stopped.status_code == 200

    prediction = client.post(
        "/api/monitoring/predict",
        headers=auth(token),
        json={"image_base64": "data:image/jpeg;base64,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "session_id": session_id},
    )
    assert prediction.status_code == 409

    observation = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={
            "session_id": session_id,
            "elderly_id": profiles[0]["id"],
            "expression": "happy",
            "confidence": 0.9,
            "observed_at": "2026-09-06T12:00:00Z",
        },
    )
    assert observation.status_code == 409


def test_observation_profile_must_match_session(client, token):
    profiles = client.get("/api/elderly", headers=auth(token)).json()
    extra = client.post(
        "/api/elderly",
        headers=auth(token),
        json={"elderly_code": "TEST-MISMATCH", "full_name": "Test Profile", "age": 70},
    )
    assert extra.status_code in (201, 400)
    profiles = client.get("/api/elderly", headers=auth(token)).json()
    session = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profiles[0]["id"]},
    ).json()
    observation = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={
            "session_id": session["session_id"],
            "elderly_id": next(profile["id"] for profile in profiles if profile["id"] != session["elderly_id"]),
            "expression": "happy",
            "confidence": 0.9,
            "observed_at": "2026-09-06T12:00:00Z",
        },
    )
    assert observation.status_code == 400


def test_starting_session_ends_prior_active_session(client, token):
    profiles = client.get("/api/elderly", headers=auth(token)).json()
    first = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profiles[0]["id"]},
    ).json()
    second = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profiles[1]["id"]},
    ).json()

    old_prediction = client.post(
        "/api/monitoring/predict",
        headers=auth(token),
        json={
            "image_base64": "data:image/jpeg;base64," + ("A" * 32),
            "session_id": first["session_id"],
        },
    )
    assert old_prediction.status_code == 409

    ended = client.post(
        f"/api/monitoring/sessions/{first['session_id']}/stop",
        headers=auth(token),
    )
    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"
    assert ended.json()["ended_at"].endswith("Z")

    stopped = client.post(
        f"/api/monitoring/sessions/{second['session_id']}/stop",
        headers=auth(token),
    )
    assert stopped.status_code == 200


def test_observation_expression_validation_and_utc_normalization(client, token):
    profile = client.get("/api/elderly", headers=auth(token)).json()[0]
    session = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profile["id"]},
    ).json()
    payload = {
        "session_id": session["session_id"],
        "elderly_id": profile["id"],
        "expression": " HAPPY ",
        "confidence": 0.91,
        "observed_at": "2026-09-06T18:15:00+05:30",
    }
    saved = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json=payload,
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["expression"] == "happy"
    assert saved.json()["observed_at"] == "2026-09-06T12:45:00Z"

    invalid = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={**payload, "expression": "joyful"},
    )
    assert invalid.status_code == 422

    missing_offset = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={**payload, "observed_at": "2026-09-06T12:45:00"},
    )
    assert missing_offset.status_code == 422


def test_report_creation_filters_observations_by_utc_period(client, token):
    profile = client.get("/api/elderly", headers=auth(token)).json()[0]
    session = client.post(
        "/api/monitoring/sessions/start",
        headers=auth(token),
        json={"elderly_id": profile["id"]},
    ).json()
    base_payload = {
        "session_id": session["session_id"],
        "elderly_id": profile["id"],
        "confidence": 0.9,
    }
    before = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={
            **base_payload,
            "expression": "happy",
            "observed_at": "2040-01-01T12:00:00Z",
        },
    )
    inside = client.post(
        "/api/monitoring/observations",
        headers=auth(token),
        json={
            **base_payload,
            "expression": "sad",
            "observed_at": "2040-01-03T17:30:00+05:30",
        },
    )
    assert before.status_code == 201
    assert inside.status_code == 201

    report = client.post(
        "/api/reports",
        headers=auth(token),
        json={
            "elderly_id": profile["id"],
            "title": "Filtered UTC report",
            "period_start": "2040-01-02T00:00:00Z",
            "period_end": "2040-01-04T00:00:00Z",
        },
    )
    assert report.status_code == 201, report.text
    body = report.json()
    assert "Observations: 1." in body["summary"]
    assert "'sad': 1" in body["summary"]
    assert body["period_start"] == "2040-01-02T00:00:00Z"
    assert body["period_end"] == "2040-01-04T00:00:00Z"

    exported = client.get(
        f"/api/reports/{body['id']}/export",
        headers=auth(token),
    )
    assert exported.status_code == 200
    assert "Filtered UTC report" in exported.json()["content"]

    reversed_period = client.post(
        "/api/reports",
        headers=auth(token),
        json={
            "elderly_id": profile["id"],
            "title": "Invalid period",
            "period_start": "2040-01-04T00:00:00Z",
            "period_end": "2040-01-02T00:00:00Z",
        },
    )
    assert reversed_period.status_code == 422


def test_demo_mode_temporal_smoothing_advances_to_five_frames():
    recognizer = ExpressionRecognizer(demo_mode=True)
    recognizer.decode_image = lambda _image: np.zeros((120, 120, 3), dtype=np.uint8)
    recognizer.detect_faces = lambda _image: [(0, 0, 120, 120)]

    windows = [
        recognizer.predict("unused", "demo-smoothing")["smoothing_window"]
        for _ in range(7)
    ]
    assert windows == [1, 2, 3, 4, 5, 5, 5]
