from fastapi.testclient import TestClient

from amader_home_assistant.main import create_app


def test_liveness_reports_ok() -> None:
    response = TestClient(create_app()).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_ok_when_services_are_available() -> None:
    response = TestClient(create_app(readiness_checker=lambda: True)).get(
        "/health/ready"
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_unavailable_when_a_service_is_down() -> None:
    response = TestClient(create_app(readiness_checker=lambda: False)).get(
        "/health/ready"
    )

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
