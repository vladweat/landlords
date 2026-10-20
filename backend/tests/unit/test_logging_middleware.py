from app.core.logging_middleware import _safe_request_path


def test_public_capability_token_is_redacted_from_request_path():
    assert (
        _safe_request_path("/v1/public/invoices/invoice-secret-token/pdf")
        == "/v1/public/invoices/[redacted]/pdf"
    )


def test_non_token_paths_are_preserved():
    assert _safe_request_path("/v1/contracts/contract-id") == "/v1/contracts/contract-id"
