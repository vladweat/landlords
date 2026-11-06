from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEMO_COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.demo.yml"


def test_demo_compose_is_a_separate_internal_sandbox() -> None:
    with DEMO_COMPOSE_PATH.open(encoding="utf-8") as source:
        compose = yaml.safe_load(source)

    assert compose["name"] == "landlords-demo"
    assert compose["networks"]["demo-sandbox"]["internal"] is True
    assert set(compose["services"]) == {
        "api",
        "db-migrate",
        "db-role-bootstrap",
        "postgres",
        "redis",
    }

    api = compose["services"]["api"]
    environment = api["environment"]
    assert "env_file" not in api
    assert environment["APP_ENV"] == "demo"
    assert environment["DB_NAME"] == "landlords_demo"
    assert environment["ALLOW_PUBLIC_REGISTRATION"] == "false"
    assert environment["YOOKASSA_SHOP_ID"] == ""
    assert environment["YOOKASSA_SECRET_KEY"] == ""
    assert environment["SMTP_HOST"] == ""
    assert environment["RESEND_API_KEY"] == ""

    api_mounts = api["volumes"]
    assert all(not str(mount).startswith((".", "/")) for mount in api_mounts)
    assert {mount.split(":", 1)[0] for mount in api_mounts} == {
        "demo_documents",
        "demo_emails",
        "demo_status",
    }
    assert compose["services"]["postgres"]["volumes"] == [
        "demo_postgres_data:/var/lib/postgresql/data"
    ]

    api_port = api["ports"][0]
    assert api_port.startswith("127.0.0.1:")
    assert "ports" not in compose["services"]["postgres"]


def test_demo_reset_requires_explicit_confirmation_and_scopes_project() -> None:
    reset_script = REPOSITORY_ROOT / "deploy/reset-demo.sh"

    source = reset_script.read_text(encoding="utf-8")

    assert '"--confirm"' in source
    assert "landlords-demo" in source
    assert "docker-compose.demo.yml" in source
    assert "down --volumes --remove-orphans" in source


def test_demo_storage_mountpoints_are_owned_by_the_runtime_user() -> None:
    dockerfile = (REPOSITORY_ROOT / "backend/Dockerfile.demo").read_text(encoding="utf-8")

    mkdir_index = dockerfile.index("mkdir -p /app/storage/documents")
    chown_index = dockerfile.index("chown -R appuser:appuser /app")
    user_index = dockerfile.index("USER appuser")

    assert mkdir_index < chown_index < user_index
    assert "/app/storage/emails" in dockerfile[mkdir_index:chown_index]
    assert "/app/storage/status" in dockerfile[mkdir_index:chown_index]
