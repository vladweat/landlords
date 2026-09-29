"""Интеграционные тесты аутентификации."""

from fastapi.testclient import TestClient

from app.core.security import create_reset_token


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
    def test_forgot_and_reset(self, client: TestClient, auth_headers, tmp_path, monkeypatch):
        """Сброс пароля: forgot пишет письмо в файл, reset меняет пароль."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

        me = client.get("/v1/auth/me", headers=auth_headers)
        user_id = me.json()["data"]["user"]["id"]

        forgot = client.post(
            "/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert forgot.status_code == 200

        files = list((tmp_path / "storage" / "emails").glob("*.txt"))
        assert files, "expected password reset email file"
        content = files[0].read_text(encoding="utf-8")
        assert "Сброс пароля" in content
        assert "reset-password?token=" in content

        token = create_reset_token(str(user_id))
        reset = client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": "newpass99"},
        )
        assert reset.status_code == 200

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
