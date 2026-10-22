from fastapi.testclient import TestClient

from app.main import create_app


def test_openapi_schema_is_disabled_outside_debug(monkeypatch):
    monkeypatch.setattr("app.main.settings.DEBUG", False)

    response = TestClient(create_app()).get("/openapi.json")

    assert response.status_code == 404


def test_openapi_schema_is_available_in_debug(monkeypatch):
    monkeypatch.setattr("app.main.settings.DEBUG", True)

    response = TestClient(create_app()).get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["openapi"]
