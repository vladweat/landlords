"""Интеграционные тесты аутентификации."""

import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    def test_register_success(self, client: TestClient):
        """Успешная регистрация."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secret123",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"

    def test_register_duplicate_email(self, client: TestClient, auth_headers):
        """Регистрация с уже существующим email."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "secret123",
                "full_name": "Duplicate",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["status"] == "error"

    def test_register_invalid_email(self, client: TestClient):
        """Регистрация с некорректным email."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "secret123",
                "full_name": "Bad Email",
            },
        )
        assert resp.status_code == 422


class TestAuthLogin:
    def test_login_success(self, client: TestClient, auth_headers):
        """Успешный вход."""
        resp = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "secret123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "token" in data

    def test_login_wrong_password(self, client: TestClient, auth_headers):
        """Неверный пароль."""
        resp = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Пользователь не существует."""
        resp = client.post(
            "/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "secret123",
            },
        )
        assert resp.status_code == 401


class TestAuthMe:
    def test_me_success(self, client: TestClient, auth_headers):
        """Получить профиль текущего пользователя."""
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "test@example.com"

    def test_me_no_token(self, client: TestClient):
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403, 422)

    def test_me_invalid_token(self, client: TestClient):
        """Невалидный токен (правильный формат, но неверная подпись)."""
        resp = client.get(
            "/auth/me",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAifQ.invalid"
            },
        )
        assert resp.status_code == 401