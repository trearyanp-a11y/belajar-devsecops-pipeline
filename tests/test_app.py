"""Regression checks for login security, migration, and readiness."""

import gc
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from werkzeug.security import check_password_hash

from app import app, init_db


class LoginTests(unittest.TestCase):
    """Use real SQLite databases without touching the developer's data."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_directory = Path.cwd()
        self.previous_config = app.config.copy()
        self.previous_password = os.environ.get("ADMIN_PASSWORD")
        self.password = secrets.token_urlsafe(24)
        os.environ["ADMIN_PASSWORD"] = self.password
        os.chdir(self.directory.name)
        self.database = Path(self.directory.name) / "users.db"
        app.config.update(TESTING=True, DATABASE=str(self.database))
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous_config)
        if self.previous_password is None:
            os.environ.pop("ADMIN_PASSWORD", None)
        else:
            os.environ["ADMIN_PASSWORD"] = self.previous_password
        os.chdir(self.previous_directory)
        gc.collect()
        self.directory.cleanup()

    def stored_passwords(self):
        """Read account data through a separate real connection."""
        connection = sqlite3.connect(self.database)
        try:
            return connection.execute(
                "SELECT username, password FROM users ORDER BY username"
            ).fetchall()
        finally:
            connection.close()

    def test_seeded_password_is_hashed_and_login_works(self):
        """Removing hashing or ignoring the configured seed breaks this check."""
        init_db()
        username, stored = self.stored_passwords()[0]
        self.assertEqual(username, "admin")
        self.assertNotEqual(stored, self.password)
        self.assertTrue(check_password_hash(stored, self.password))
        response = self.client.post(
            "/", data={"username": "admin", "password": self.password}
        )
        self.assertIn(b"Login Berhasil", response.data)

    def test_plaintext_migration_preserves_accounts_and_is_idempotent(self):
        """A second startup must neither lose accounts nor hash hashes again."""
        connection = sqlite3.connect(self.database)
        connection.execute("CREATE TABLE users (username TEXT, password TEXT)")
        connection.execute("INSERT INTO users VALUES (?, ?)", ("admin", self.password))
        connection.execute("INSERT INTO users VALUES (?, ?)", ("student", self.password))
        connection.commit()
        connection.close()
        init_db()
        first = self.stored_passwords()
        init_db()
        self.assertEqual(self.stored_passwords(), first)
        self.assertEqual([row[0] for row in first], ["admin", "student"])
        self.assertTrue(all(check_password_hash(row[1], self.password) for row in first))
        response = self.client.post(
            "/", data={"username": "student", "password": self.password}
        )
        self.assertIn(b"Login Berhasil", response.data)

    def test_empty_database_requires_an_explicit_seed_password(self):
        """An empty installation must not silently create a shared password."""
        os.environ.pop("ADMIN_PASSWORD", None)
        with self.assertRaisesRegex(RuntimeError, "ADMIN_PASSWORD"):
            init_db()

    def test_readiness_detects_missing_and_corrupt_database(self):
        """A fixed JSON response must not mark unavailable storage ready."""
        init_db()
        self.assertEqual(self.client.get("/health").status_code, 200)
        gc.collect()
        self.database.unlink()
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(self.database.exists())
        self.database.write_bytes(b"not a sqlite database")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(str(self.database).encode(), response.data)

    def test_liveness_is_independent_of_storage(self):
        """A DB outage should affect readiness without forcing restart loops."""
        self.assertEqual(self.client.get("/live").status_code, 200)

    def test_wrong_password_and_sql_injection_are_rejected(self):
        """Untrusted login values must never bypass the password check."""
        init_db()
        for username in ("admin", "admin' OR '1'='1' --", "missing"):
            with self.subTest(username=username):
                response = self.client.post(
                    "/", data={"username": username, "password": "wrong"}
                )
                self.assertIn(b"Login Gagal", response.data)

    def test_about_identifies_the_deployed_revision(self):
        """Deployment verification must distinguish old and new artifacts."""
        response = self.client.get("/about")
        self.assertEqual(response.status_code, 200)
        self.assertIn("revision", response.json)
        self.assertEqual(response.json["revision"], os.getenv("APP_REVISION", "local"))

    def test_parallel_startup_does_not_duplicate_the_seed(self):
        """Two pod processes must serialize their shared DB initialization."""
        environment = os.environ.copy()
        environment["DATABASE_PATH"] = str(self.database)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", "from app import init_db; init_db()"],
                env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        for process in processes:
            _, error = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, error.decode())
        rows = self.stored_passwords()
        self.assertEqual(len(rows), 1)
        self.assertTrue(check_password_hash(rows[0][1], self.password))


if __name__ == "__main__":
    unittest.main()
