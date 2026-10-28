"""Behavioral checks for the host-side Landlords backup script."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "deploy" / "backup-landlords.sh"


class BackupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="landlords-backup-test-")
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "docker-compose.yml").write_text("services: {}\n")
        (self.project / "docker-compose.production.yml").write_text("services: {}\n")
        (self.project / "storage" / "documents").mkdir(parents=True)
        (self.project / "storage" / "documents" / "lease.pdf").write_bytes(b"demo document")
        self.backup_dir = self.root / "backups"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.dump = self.root / "mock.dump"
        self.dump.write_bytes(b"mock postgres custom dump")
        self._write_docker_stub()

    def tearDown(self):
        self.temp.cleanup()

    def _write_docker_stub(self):
        docker = self.bin_dir / "docker"
        docker.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"${MOCK_DOCKER_LOG:-/dev/null}\"\n"
            "case \"$*\" in\n"
            "  *'config --quiet'*) exit 0 ;;\n"
            "  *'ps --services'*) printf 'postgres\\n'; exit 0 ;;\n"
            "  *pg_dump*) [ \"${MOCK_DUMP_FAIL:-0}\" = 0 ] || exit 42; cat \"$MOCK_DUMP\" ;;\n"
            "  *) echo \"unexpected docker invocation: $*\" >&2; exit 43 ;;\n"
            "esac\n"
        )
        docker.chmod(0o755)

    def _run_backup(self, *, dump_fail=False):
        env = os.environ.copy()
        env.update(
            {
                "PROJECT_DIR": str(self.project),
                "BACKUP_DIR": str(self.backup_dir),
                "BACKUP_CONFIG_FILE": "/dev/null",
                "PATH": f"{self.bin_dir}:{env['PATH']}",
                "MOCK_DUMP": str(self.dump),
                "MOCK_DUMP_FAIL": "1" if dump_fail else "0",
                "RETENTION_DAYS": "14",
            }
        )
        return subprocess.run(
            ["bash", str(SCRIPT)], capture_output=True, text=True, env=env, check=False
        )

    def test_success_publishes_complete_checksummed_database_and_documents(self):
        result = self._run_backup()

        self.assertEqual(result.returncode, 0, result.stderr)
        sets = list(self.backup_dir.glob("landlords-*/COMPLETE"))
        self.assertEqual(len(sets), 1)
        backup_set = sets[0].parent
        self.assertEqual((backup_set / "database.dump").read_bytes(), self.dump.read_bytes())
        self.assertEqual(
            (backup_set / "documents.tar.gz").stat().st_size > 0,
            True,
        )
        checksum = (backup_set / "SHA256SUMS").read_text().splitlines()
        self.assertEqual(len(checksum), 2)
        for line in checksum:
            digest, filename = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((backup_set / filename).read_bytes()).hexdigest(), digest)
        self.assertEqual((backup_set / "COMPLETE").read_text().strip(), "complete")
        self.assertEqual((backup_set.stat().st_mode & 0o077), 0)

    def test_failed_dump_does_not_publish_partial_backup(self):
        result = self._run_backup(dump_fail=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("No such file or directory", result.stderr)
        self.assertEqual(list(self.backup_dir.glob("landlords-*/COMPLETE")), [])
        self.assertEqual(list(self.backup_dir.glob(".landlords-tmp-*")), [])

    def test_retention_removes_only_expired_completed_landlords_sets(self):
        expired = self.backup_dir / "landlords-20000101T000000Z"
        expired.mkdir(parents=True)
        (expired / "COMPLETE").write_text("complete\n")
        os.utime(expired, (1, 1))
        unrelated = self.backup_dir / "keep-me.txt"
        unrelated.write_text("keep")

        result = self._run_backup()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(expired.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(len(list(self.backup_dir.glob("landlords-*/COMPLETE"))), 1)

    def test_restore_check_rejects_tampered_set_before_starting_docker(self):
        backup_set = self.backup_dir / "landlords-20261028T000000Z"
        backup_set.mkdir(parents=True)
        (backup_set / "database.dump").write_bytes(b"dump")
        (backup_set / "documents.tar.gz").write_bytes(b"archive")
        (backup_set / "SHA256SUMS").write_text(
            f"{hashlib.sha256(b'dump').hexdigest()}  database.dump\n"
            f"{hashlib.sha256(b'archive').hexdigest()}  documents.tar.gz\n"
        )
        (backup_set / "COMPLETE").write_text("complete\n")
        (backup_set / "database.dump").write_bytes(b"tampered")
        docker_log = self.root / "docker.log"
        env = os.environ.copy()
        env.update(
            {
                "PROJECT_DIR": str(self.project),
                "BACKUP_DIR": str(self.backup_dir),
                "BACKUP_CONFIG_FILE": "/dev/null",
                "PATH": f"{self.bin_dir}:{env['PATH']}",
                "MOCK_DOCKER_LOG": str(docker_log),
            }
        )

        result = subprocess.run(
            ["bash", str(REPO / "deploy" / "restore-check-landlords.sh"), str(backup_set)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("No such file or directory", result.stderr)
        self.assertFalse(docker_log.exists() and docker_log.read_text())


if __name__ == "__main__":
    unittest.main()
