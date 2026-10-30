"""Regression checks for login security, migration, and readiness."""

import gc
import os
from pathlib import Path
import secrets
import re
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
        app.config.update(TESTING=True, DATABASE=str(self.database),
                          SECRET_KEY=secrets.token_hex(32))
        self.client = app.test_client()

    def csrf(self):
        """Obtain the same token a browser reads from the rendered login form."""
        response = self.client.get("/")
        return re.search(rb'name="csrf_token" value="([^"]+)"', response.data)[1].decode()

    def login(self, username="admin", password=None):
        """Exercise login with a genuine browser-issued CSRF token."""
        return self.client.post("/", data={
            "username": username, "password": password or self.password,
            "csrf_token": self.csrf(),
        })

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
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/game"))
        self.assertEqual(self.client.get("/game").status_code, 200)

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
        response = self.login("student")
        self.assertEqual(response.status_code, 302)

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
                response = self.login(username, "wrong")
                self.assertIn(b"Login Gagal", response.data)
                self.assertEqual(self.client.get("/game").status_code, 302)

    def test_anonymous_game_and_apis_are_protected(self):
        """Knowing a URL must not bypass login."""
        init_db()
        self.assertEqual(self.client.get("/game").status_code, 302)
        for route in ("/api/leaderboard", "/api/search?player_name=admin"):
            self.assertEqual(self.client.get(route).status_code, 401)
        self.assertEqual(self.client.post("/api/score", json={}).status_code, 401)

    def test_csrf_is_required_for_login_score_and_logout(self):
        """Cross-site form/JSON requests must not change authentication or scores."""
        init_db()
        self.assertEqual(self.client.post("/", data={
            "username": "admin", "password": self.password,
        }).status_code, 400)
        self.login()
        self.assertEqual(self.client.post("/api/score", json={
            "score": 10, "duration_seconds": 1,
        }).status_code, 400)
        self.assertEqual(self.client.post("/logout").status_code, 400)
        self.assertEqual(self.client.post("/api/score", json={}, headers={
            "X-CSRF-Token": "token-salah-é",
        }).status_code, 400)
        self.assertEqual(self.client.get("/game").status_code, 200)

    def test_score_uses_logged_in_account_and_survives_startup(self):
        """A submitted player_name must not impersonate another account."""
        init_db()
        self.login()
        token = self.client.get("/game").data
        token = re.search(rb'name="csrf-token" content="([^"]+)"', token)[1].decode()
        response = self.client.post("/api/score", json={
            "player_name": "someone_else", "score": 120, "duration_seconds": 4.5,
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 201)
        init_db()
        rows = self.client.get("/api/leaderboard").json
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player_name"], "admin")
        self.assertEqual(rows[0]["score"], 120)
        self.assertEqual(self.client.get("/api/search?player_name=admin").json, rows)
        self.assertEqual(self.client.get(
            "/api/search", query_string={"player_name": "' OR 1=1 --"}
        ).json, [])
        self.assertEqual(self.client.post("/logout", data={
            "csrf_token": token,
        }).status_code, 302)
        self.assertEqual(self.client.get("/game").status_code, 302)
        self.assertEqual(self.client.get("/api/leaderboard").status_code, 401)

    def test_invalid_score_payloads_do_not_write_rows(self):
        """Malformed JSON and non-finite or coerced numeric values are rejected."""
        init_db()
        self.login()
        token = re.search(rb'name="csrf-token" content="([^"]+)"',
                          self.client.get("/game").data)[1].decode()
        for payload in ([], None, {}, {"score": True, "duration_seconds": 1},
                        {"score": -1, "duration_seconds": 1},
                        {"score": "10", "duration_seconds": 1},
                        {"score": 10, "duration_seconds": float("nan")},
                        {"score": 10, "duration_seconds": float("inf")},
                        {"score": 10, "duration_seconds": -1}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/score", json=payload,
                                            headers={"X-CSRF-Token": token})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/leaderboard").json, [])

    def test_session_can_be_read_by_other_pod_but_not_another_key(self):
        """A shared secret enables load balancing; a different secret rejects it."""
        init_db()
        self.login()
        other = app.test_client()
        other.set_cookie("session", self.client.get_cookie("session").value)
        self.assertEqual(other.get("/game").status_code, 200)
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        self.assertEqual(other.get("/game").status_code, 302)

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
