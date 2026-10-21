"""Интеграционные тесты аутентификации."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import ALGORITHM, SECRET_KEY


class TestAuthRegister:
    def test_register_success(self, client: TestClient):
        """Успешная регистрация."""
        resp = client.post(
            "/v1/auth/register",
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

    def test_register_omits_bearer_token_when_not_requested(self, client: TestClient):
        response = TestClient(client.app).post(
            "/v1/auth/register",
            json={
                "email": "cookie-only@example.com",
                "password": "secret123",
                "full_name": "Cookie Only",
            },
        )

        assert response.status_code == 200
        assert "token" not in response.json()
        assert response.cookies.get("access_token")

    def test_register_duplicate_email(self, client: TestClient, auth_headers):
        """Регистрация с уже существующим email."""
        resp = client.post(
            "/v1/auth/register",
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
            "/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "secret123",
                "full_name": "Bad Email",
            },
        )
        assert resp.status_code == 422

    def test_register_forbidden_when_disabled(self, client: TestClient, monkeypatch):
        """Публичная регистрация выключена флагом."""
        monkeypatch.setattr(
            "app.api.v1.routes.auth.settings.ALLOW_PUBLIC_REGISTRATION",
            False,
        )
        resp = client.post(
            "/v1/auth/register",
            json={
                "email": "closed@example.com",
                "password": "secret123",
                "full_name": "Closed",
            },
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["status"] == "error"
        assert "закрыта" in body["message"].lower()


class TestAuthLogin:
    def test_login_success(self, client: TestClient, auth_headers):
        """Успешный вход."""
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "secret123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "token" in data

    def test_login_omits_bearer_token_when_not_requested(
        self, client: TestClient, auth_headers
    ):
        response = TestClient(client.app).post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "secret123"},
        )

        assert response.status_code == 200
        assert "token" not in response.json()
        assert response.cookies.get("access_token")

    def test_login_sets_access_cookie(self, client: TestClient, auth_headers):
        """Вход кладёт JWT в HttpOnly-cookie."""
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "secret123",
            },
        )
        assert resp.status_code == 200
        token = resp.json()["token"]
        assert resp.cookies.get("access_token") == token
        set_cookie = resp.headers["set-cookie"]
        assert "access_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/" in set_cookie
        assert "SameSite=lax" in set_cookie

    def test_production_cookie_is_secure(self, client: TestClient, auth_headers, monkeypatch):
        monkeypatch.setattr("app.core.cookies.settings.APP_ENV", "production")
        response = client.post(
            "/v1/auth/login",
            headers={"X-Return-Bearer-Token": "false"},
            json={"email": "test@example.com", "password": "secret123"},
        )

        assert response.status_code == 200
        set_cookie = response.headers["set-cookie"]
        assert "Secure" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie

    def test_cookie_mutation_rejects_foreign_origin(self, client: TestClient, auth_headers):
        response = client.post(
            "/v1/auth/logout",
            headers={"Origin": "https://attacker.example"},
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Cross-site request blocked"

    def test_cookie_mutation_accepts_configured_origin(self, client: TestClient, auth_headers):
        response = client.post(
            "/v1/auth/logout",
            headers={"Origin": settings.FRONTEND_URL},
        )

        assert response.status_code == 200
        assert "Max-Age=0" in response.headers["set-cookie"]
        assert client.get("/v1/auth/me").status_code == 401

    def test_cookie_mutation_rejects_null_origin_when_config_is_invalid(
        self, client: TestClient, auth_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "FRONTEND_URL", "null")
        response = client.put(
            "/v1/auth/me",
            headers={"Origin": "null"},
            json={"full_name": "Should not change"},
        )

        assert response.status_code == 403

    def test_logout_revokes_bearer_copy_of_session(self, client: TestClient, auth_headers):
        response = client.post("/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert client.get("/v1/auth/me", headers=auth_headers).status_code == 401

    def test_access_token_without_server_session_id_is_rejected(self, client: TestClient):
        token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000001",
                "account_id": "00000000-0000-0000-0000-000000000002",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        response = client.get(
            "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401

    def test_login_wrong_password(self, client: TestClient, auth_headers):
        """Неверный пароль."""
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Пользователь не существует."""
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "secret123",
            },
        )
        assert resp.status_code == 401


class TestAuthMe:
    def test_me_success(self, client: TestClient, auth_headers):
        """Получить профиль текущего пользователя."""
        resp = client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["user"]["email"] == "test@example.com"
        assert data["data"]["role"] == "owner"
        assert "id" in data["data"]["account"]

    def test_me_with_cookie_without_bearer(self, client: TestClient, auth_headers):
        """Профиль открывается по cookie сессии, без заголовка Authorization."""
        login = client.post(
            "/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "secret123",
            },
        )
        assert login.status_code == 200
        client.cookies.clear()
        client.cookies.set("access_token", login.cookies["access_token"])

        resp = client.get("/v1/auth/me")
        assert "authorization" not in {k.lower() for k in resp.request.headers}
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["user"]["email"] == "test@example.com"

    def test_me_no_token(self, client: TestClient):
        resp = client.get("/v1/auth/me")
        assert resp.status_code in (401, 403, 422)

    def test_me_invalid_token(self, client: TestClient):
        """Невалидный токен (правильный формат, но неверная подпись)."""
        resp = client.get(
            "/v1/auth/me",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAifQ.invalid"
            },
        )
        assert resp.status_code == 401


class TestPasswordReset:
    def test_change_password_revokes_all_sessions(
        self, client: TestClient, auth_headers
    ):
        response = client.post(
            "/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "secret123", "new_password": "newpass99"},
        )

        assert response.status_code == 200
        assert "Max-Age=0" in response.headers["set-cookie"]
        assert client.get("/v1/auth/me", headers=auth_headers).status_code == 401

    def test_forgot_and_reset(self, client: TestClient, auth_headers, tmp_path, monkeypatch):
        """Сброс пароля: forgot пишет письмо в файл, reset меняет пароль."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

        forgot = client.post(
            "/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert forgot.status_code == 200

        files = list((tmp_path / "storage" / "emails").glob("*.txt"))
        assert files, "expected password reset email file"
        content = files[0].read_text(encoding="utf-8")
        assert "Сброс пароля" in content
        assert "reset-password#token=" in content

        reset_link = next(
            line.strip()
            for line in content.splitlines()
            if "/reset-password#token=" in line
        )
        token = parse_qs(urlsplit(reset_link).fragment)["token"][0]
        reset = client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": "newpass99"},
        )
        assert reset.status_code == 200
        replay = client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": "anotherpass99"},
        )
        assert replay.status_code == 422
        assert client.get("/v1/auth/me", headers=auth_headers).status_code == 401

        old_login = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "secret123"},
        )
        assert old_login.status_code == 401

        new_login = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "newpass99"},
        )
        assert new_login.status_code == 200

    def test_forgot_unknown_email_ok(self, client: TestClient):
        """Несуществующий email не раскрывает факт отсутствия."""
        resp = client.post(
            "/v1/auth/forgot-password",
            json={"email": "missing@example.com"},
        )
        assert resp.status_code == 200

    def test_reset_rejects_invalid_token(self, client: TestClient):
        response = client.post(
            "/v1/auth/reset-password",
            json={"token": "not-a-jwt", "new_password": "newpass99"},
        )

        assert response.status_code == 422

    def test_reset_rejects_token_without_one_time_id(self, client: TestClient):
        token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000001",
                "type": "reset",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        response = client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": "newpass99"},
        )

        assert response.status_code == 422

    def test_reset_rejects_expired_token(self, client: TestClient):
        expired = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000001",
                "jti": "00000000-0000-0000-0000-000000000003",
                "type": "reset",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        response = client.post(
            "/v1/auth/reset-password",
            json={"token": expired, "new_password": "newpass99"},
        )

        assert response.status_code == 422
