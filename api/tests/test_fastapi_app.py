import pytest

from fastapi.testclient import TestClient

from npnkorea.web.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_to_npn_endpoint_returns_expected_json() -> None:
    response = client.post(
        "/to-npn",
        json={
            "points": [{"lon": 126.978422, "lat": 37.566742}],
            "output": "han",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"results": ["다사 5393 5205"]}


def test_to_wgs_endpoint_returns_expected_json_shape() -> None:
    response = client.post(
        "/to-wgs",
        json={
            "codes": ["다사 5396 5207", "MaRa43478827"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["results"]
    assert len(payload["results"]) == 2
    assert set(payload["results"][0]) == {"lon", "lat"}


def test_core_validation_surfaces_as_http_422() -> None:
    response = client.post(
        "/to-npn",
        json={
            "points": [{"lon": 124.000001, "lat": 33.0}],
            "output": "han",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "`points` contains coordinates outside the supported NPN grid after projection."
    }


def test_batch_size_is_limited() -> None:
    points = [{"lon": 126.978422, "lat": 37.566742}] * 1001
    response = client.post("/to-npn", json={"points": points})

    assert response.status_code == 422


def test_localhost_origin_is_allowed_by_cors() -> None:
    response = client.options(
        "/to-npn",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
