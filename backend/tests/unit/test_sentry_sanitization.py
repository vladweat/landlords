from app.main import _sanitize_sentry_event


def test_sentry_redacts_public_tokens_queries_and_auth_headers():
    event = {
        "request": {
            "url": "https://example.test/v1/public/invites/secret-token/accept?token=query-secret",
            "query_string": "token=query-secret",
            "data": {"token": "body-secret", "password": "password-secret"},
            "cookies": {"access_token": "cookie-secret"},
            "headers": {
                "Authorization": "Bearer bearer-secret",
                "Cookie": "access_token=cookie-secret",
                "Accept": "application/json",
            },
        },
        "transaction": "POST /v1/public/invites/secret-token/accept",
    }

    result = _sanitize_sentry_event(event)

    assert result["request"]["url"] == (
        "https://example.test/v1/public/invites/[redacted]/accept"
    )
    assert result["transaction"] == "POST /v1/public/invites/[redacted]/accept"
    assert "query_string" not in result["request"]
    assert "data" not in result["request"]
    assert "cookies" not in result["request"]
    assert result["request"]["headers"] == {"Accept": "application/json"}
