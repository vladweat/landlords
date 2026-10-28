import hashlib
import json
import os

import pytest

from app.scripts.provision_redis_acl import provision, refresh_acl


def test_provision_creates_distinct_secrets_and_acl_hashes_without_printing_values(
    tmp_path, capsys
):
    output_dir = tmp_path / "secrets" / "redis"

    provision(output_dir)

    passwords = {
        name: (output_dir / f"{name}.password").read_text(encoding="utf-8").strip()
        for name in ("api", "worker", "flower", "exporter")
    }
    acl = (output_dir / "users.acl").read_text(encoding="utf-8")
    exporter_passwords = json.loads(
        (output_dir / "exporter-passwords.json").read_text(encoding="utf-8")
    )
    assert exporter_passwords == {
        "redis://landlords_exporter@redis:6379": passwords["exporter"]
    }
    assert len(set(passwords.values())) == 4
    assert "user default off" in acl
    assert "user landlords_health on nopass resetkeys resetchannels ~* +ping" in acl
    assert "~landlords:ops:*" in acl
    assert "resetkeys resetchannels ~landlords:*" in acl
    assert "&landlords:/0.celery.pidbox" in acl
    worker_acl = next(line for line in acl.splitlines() if line.startswith("user landlords_worker "))
    flower_acl = next(line for line in acl.splitlines() if line.startswith("user landlords_flower "))
    exporter_acl = next(line for line in acl.splitlines() if line.startswith("user landlords_exporter "))
    assert "&landlords:/0.celeryev/worker.*" in worker_acl
    assert "&landlords:/0.celeryev/*" in flower_acl
    assert "&landlords:celery-task-meta-*" in worker_acl
    assert "&landlords:celery-task-meta-*" in flower_acl
    assert "&/0.celery.pidbox" not in acl
    assert "&landlords:/0.celeryev/#" not in acl
    assert "&landlords:/0.celeryev/worker.#" not in acl
    assert "&landlords:*" not in acl
    assert "-@all" in exporter_acl
    assert "+info" in exporter_acl
    assert "+ping" in exporter_acl
    assert "+config|get" in exporter_acl
    assert "+client" in exporter_acl
    assert "~landlords:*" in exporter_acl
    assert "+@all" not in exporter_acl
    for password in passwords.values():
        assert password not in acl
        assert hashlib.sha256(password.encode()).hexdigest() in acl
    assert all(password not in capsys.readouterr().out for password in passwords.values())
    if os.name != "nt":
        assert output_dir.stat().st_mode & 0o777 == 0o700
        assert (output_dir / "api.password").stat().st_mode & 0o777 == 0o644
        assert (output_dir / "users.acl").stat().st_mode & 0o777 == 0o644


def test_refresh_acl_preserves_password_files_and_never_prints_passwords(
    tmp_path, capsys
):
    output_dir = tmp_path / "redis"
    provision(output_dir)
    passwords = {
        name: (output_dir / f"{name}.password").read_bytes()
        for name in ("api", "worker", "flower", "exporter")
    }
    exporter_config = (output_dir / "exporter-passwords.json").read_bytes()

    refresh_acl(output_dir)

    acl = (output_dir / "users.acl").read_text(encoding="utf-8")
    assert "user default off" in acl
    assert "&landlords:/0.celery.pidbox" in acl
    assert "&landlords:celery-task-meta-*" in acl
    assert "&landlords:/0.celeryev/worker.*" in acl
    for name, password in passwords.items():
        assert (output_dir / f"{name}.password").read_bytes() == password
        assert hashlib.sha256(password.strip()).hexdigest() in acl
        assert password.decode().strip() not in capsys.readouterr().out
    assert (output_dir / "exporter-passwords.json").read_bytes() == exporter_config


def test_provision_uses_configured_key_prefix_for_keys_and_pubsub_channels(tmp_path):
    output_dir = tmp_path / "redis"

    provision(output_dir, key_prefix="custom:")

    acl = (output_dir / "users.acl").read_text(encoding="utf-8")
    assert "~custom:ops:*" in acl
    assert "~custom:*" in acl
    assert "&custom:/0.celery.pidbox" in acl
    assert "&custom:celery-task-meta-*" in acl
    assert "&custom:/0.celeryev/worker.*" in acl
    assert "&custom:/0.celeryev/*" in acl


@pytest.mark.parametrize("key_prefix", ("", "unsafe*:", "white space:", "missing-colon"))
def test_provision_rejects_key_prefixes_that_could_expand_acl_scope(tmp_path, key_prefix):
    with pytest.raises(ValueError, match="Redis key prefix"):
        provision(tmp_path / "redis", key_prefix=key_prefix)


def test_provision_refuses_to_overwrite_existing_secret(tmp_path):
    output_dir = tmp_path / "redis"
    output_dir.mkdir()
    existing = output_dir / "api.password"
    existing.write_text("preserve-me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        provision(output_dir)

    assert existing.read_text(encoding="utf-8") == "preserve-me"
