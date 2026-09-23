"""HTTP-level tests for the FastAPI app."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_adjudicate_unique():
    payload = {
        "streamA": [
            {"time": 1, "code": "A"},
            {"time": 2, "code": "B"},
        ],
        "streamB": [
            {"time": 1, "code": "A"},
            {"time": 2, "code": "B"},
        ],
        "minOffset": -1,
        "maxOffset": 1,
        "jump": 0,
        "minHits": 2,
    }
    r = client.post("/api/adjudicate", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["feasible"] is True
    assert body["matchCount"] == 2
    assert body["uniqueness"] == "unique"
    assert body["solution"]["initialOffset"] == 0
    assert body["solution"]["jumpDirection"] == "none"
    assert body["solution"]["pairs"][0]["timeA"] == 1


def test_adjudicate_ambiguous_has_witness():
    payload = {
        "streamA": [{"time": t, "code": "X"} for t in (1, 2)],
        "streamB": [{"time": t, "code": "X"} for t in (1, 2, 3)],
        "minOffset": -1,
        "maxOffset": 1,
        "jump": 0,
        "minHits": 1,
    }
    r = client.post("/api/adjudicate", json=payload)
    body = r.json()
    assert r.status_code == 200
    assert body["uniqueness"] == "ambiguous"
    assert body["witness"] is not None
    assert body["witness"]["pairIndices"] != body["solution"]["pairIndices"]


def test_adjudicate_infeasible_below_min_hits():
    payload = {
        "streamA": [{"time": 0, "code": "A"}, {"time": 100, "code": "B"}],
        "streamB": [{"time": 0, "code": "Z"}, {"time": 100, "code": "Y"}],
        "minOffset": 0,
        "maxOffset": 0,
        "jump": 0,
        "minHits": 1,
    }
    r = client.post("/api/adjudicate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["feasible"] is False
    assert body["solution"] is None
    assert body["reason"]


def test_validation_rejects_non_increasing():
    payload = {
        "streamA": [{"time": 5, "code": "A"}, {"time": 5, "code": "B"}],
        "streamB": [{"time": 1, "code": "A"}, {"time": 2, "code": "B"}],
        "minOffset": 0,
        "maxOffset": 0,
        "jump": 0,
        "minHits": 1,
    }
    r = client.post("/api/adjudicate", json=payload)
    assert r.status_code == 422


def test_validation_rejects_bad_code_and_length():
    payload = {
        "streamA": [{"time": 0, "code": "ab"}],
        "streamB": [{"time": 1, "code": "A"}, {"time": 2, "code": "B"}],
        "minOffset": 0,
        "maxOffset": 0,
        "jump": 0,
        "minHits": 1,
    }
    assert client.post("/api/adjudicate", json=payload).status_code == 422

    payload["streamA"] = [{"time": 0, "code": "A"}]
    assert client.post("/api/adjudicate", json=payload).status_code == 422


def test_validation_large_values_accepted():
    payload = {
        "streamA": [
            {"time": 0, "code": "A1"},
            {"time": 10**12, "code": "ZZZZZZZZ"},
        ],
        "streamB": [
            {"time": 0, "code": "A1"},
            {"time": 10**12, "code": "ZZZZZZZZ"},
        ],
        "minOffset": -(10**12),
        "maxOffset": 10**12,
        "jump": 10**12,
        "minHits": 2,
    }
    r = client.post("/api/adjudicate", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["matchCount"] == 2
