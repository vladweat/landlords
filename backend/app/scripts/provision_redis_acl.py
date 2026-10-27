"""Provision host-only Redis passwords and refresh a hash-only ACL file."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
from pathlib import Path

DEFAULT_KEY_PREFIX = "landlords:"
KEY_PREFIX_PATTERN = re.compile(r"[A-Za-z0-9_-]+:")


def provision(output_dir: Path, key_prefix: str = DEFAULT_KEY_PREFIX) -> None:
    """Create independent credentials without printing or overwriting secrets."""
    output_dir = Path(output_dir)
    key_prefix = _validate_key_prefix(key_prefix)
    identities = {
        "api": "landlords_api",
        "worker": "landlords_worker",
        "flower": "landlords_flower",
    }
    paths = [output_dir / f"{name}.password" for name in identities]
    acl_path = output_dir / "users.acl"
    existing = [path.name for path in [*paths, acl_path] if path.exists()]
    if existing:
        raise FileExistsError(
            "Redis secret files already exist; rotate them through the deployment runbook"
        )

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(output_dir, 0o700)

    passwords = {name: secrets.token_urlsafe(48) for name in identities}
    for name, password in passwords.items():
        _write_private_file(output_dir / f"{name}.password", f"{password}\n")

    _write_acl_file(output_dir, passwords, key_prefix=key_prefix, replace=False)


def refresh_acl(output_dir: Path, key_prefix: str = DEFAULT_KEY_PREFIX) -> None:
    """Refresh ACL rules from existing password files without rotating credentials."""
    output_dir = Path(output_dir)
    key_prefix = _validate_key_prefix(key_prefix)
    identities = ("api", "worker", "flower")
    missing = [
        f"{name}.password"
        for name in identities
        if not (output_dir / f"{name}.password").is_file()
    ]
    if missing:
        raise FileNotFoundError("Required Redis password files are missing")

    passwords = {}
    for name in identities:
        try:
            password = (output_dir / f"{name}.password").read_text(encoding="utf-8").strip()
        except OSError:
            raise RuntimeError("Unable to read Redis password file") from None
        if not password:
            raise RuntimeError("Redis password file is empty")
        passwords[name] = password

    _write_acl_file(output_dir, passwords, key_prefix=key_prefix, replace=True)


def _validate_key_prefix(key_prefix: str) -> str:
    if not KEY_PREFIX_PATTERN.fullmatch(key_prefix):
        raise ValueError(
            "Redis key prefix must contain only letters, digits, '_' or '-' and end with ':'"
        )
    return key_prefix


def _write_acl_file(
    output_dir: Path,
    passwords: dict[str, str],
    *,
    key_prefix: str,
    replace: bool,
) -> None:
    identities = {
        "api": "landlords_api",
        "worker": "landlords_worker",
        "flower": "landlords_flower",
    }
    acl_lines = ["user default off"]
    for name, username in identities.items():
        password_hash = hashlib.sha256(passwords[name].encode("utf-8")).hexdigest()
        if name == "api":
            rules = (
                f"resetkeys resetchannels ~{key_prefix}ops:* "
                "+@read +@write +@connection -@admin -@dangerous"
            )
        else:
            channels = [f"&{key_prefix}/0.celery.pidbox"]
            channels.append(f"&{key_prefix}celery-task-meta-*")
            if name == "worker":
                channels.append(f"&{key_prefix}/0.celeryev/worker.*")
            else:
                channels.append(f"&{key_prefix}/0.celeryev/*")
            rules = (
                f"resetkeys resetchannels ~{key_prefix}* {' '.join(channels)} "
                "+@all -@admin -@dangerous"
            )
        acl_lines.append(f"user {username} on #{password_hash} {rules}")
    acl_lines.append("user landlords_health on nopass resetkeys resetchannels ~* +ping")
    contents = "\n".join(acl_lines) + "\n"
    acl_path = output_dir / "users.acl"

    if not replace:
        _write_private_file(acl_path, contents)
        if os.name != "nt":
            # Redis runs as UID 999; hashes are safe to read, passwords are not.
            os.chmod(acl_path, 0o644)
        return

    if not acl_path.is_file():
        raise FileNotFoundError("Redis ACL file does not exist")
    temporary_path = output_dir / f".users.acl.{secrets.token_hex(8)}.tmp"
    try:
        _write_private_file(temporary_path, contents)
        if os.name != "nt":
            os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, acl_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_private_file(path: Path, contents: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(contents)
    if os.name != "nt":
        os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--output-dir",
        type=Path,
        default=Path("secrets/redis"),
        help="host-only output directory (default: secrets/redis)",
    )
    action.add_argument(
        "--refresh-acl",
        action="store_true",
        help="refresh ACL rules from existing password files without rotating passwords",
    )
    parser.add_argument(
        "--key-prefix",
        default=os.getenv("REDIS_KEY_PREFIX", DEFAULT_KEY_PREFIX),
        help="configured Redis key prefix (default: landlords:)",
    )
    args = parser.parse_args()
    output_dir = args.output_dir
    if args.refresh_acl:
        output_dir = Path("secrets/redis")
        refresh_acl(output_dir, key_prefix=args.key_prefix)
        print(f"Redis ACL updated in {output_dir}; credentials were not displayed.")
    else:
        provision(output_dir, key_prefix=args.key_prefix)
        print(f"Redis ACL and password files created in {output_dir}; values were not displayed.")


if __name__ == "__main__":
    main()
