"""Modul backend autentikasi Flask dengan antarmuka web interaktif."""

from contextlib import closing
import os
from pathlib import Path
import sqlite3
from flask import Flask, render_template, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["DATABASE"] = os.getenv("DATABASE_PATH", "users.db")


def get_db_connection():
    """Buka SQLite pada lokasi persisten dengan batas tunggu penulis."""
    database = Path(app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(database, timeout=30)


def init_db():
    """Migrasikan password lama satu kali tanpa mengganti akun yang ada."""
    with closing(get_db_connection()) as conn:
        # Serialisasi startup dua pod agar migrasi dan seed tidak berlomba.
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT,
                password TEXT
            )
            """
        )

        if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
            for row_id, password in conn.execute("SELECT rowid, password FROM users"):
                conn.execute(
                    "UPDATE users SET password = ? WHERE rowid = ?",
                    (generate_password_hash(password), row_id),
                )
            conn.execute("PRAGMA user_version = 1")

        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None:
            password = os.getenv("ADMIN_PASSWORD")
            if not password:
                raise RuntimeError("Set ADMIN_PASSWORD untuk database kosong")
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (os.getenv("ADMIN_USERNAME", "admin"), generate_password_hash(password))
            )

        conn.commit()


@app.route("/", methods=["GET", "POST"])
def index():
    """Menampilkan formulir login dan memproses autentikasi."""
    message = None
    status_class = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()

            # Parameterized query untuk mencegah SQL Injection
            query = """
                SELECT password FROM users WHERE username = ?
            """
            cursor.execute(query, (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user[0], password):
            message = "Login Berhasil! Selamat datang."
            status_class = "success"
        else:
            message = "Login Gagal! Kredensial tidak valid."
            status_class = "danger"

    return render_template(
        "index.html",
        message=message,
        status_class=status_class
    )


@app.route("/health", methods=["GET"])
def health():
    """Readiness memeriksa database yang sudah ada tanpa membuat DB kosong."""
    database_uri = Path(app.config["DATABASE"]).resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(database_uri, uri=True, timeout=1)) as conn:
            conn.execute("SELECT username FROM users LIMIT 1").fetchone()
    except sqlite3.Error:
        return jsonify({"status": "unavailable", "service": "flask-auth-app"}), 503
    return jsonify({
        "status": "ok",
        "service": "flask-auth-app",
        "database": "ready"
    }), 200


@app.route("/live", methods=["GET"])
def live():
    """Liveness proses tetap sehat ketika penyimpanan sementara tidak siap."""
    return jsonify({"status": "ok"}), 200


@app.route("/about", methods=["GET"])
def about():
    """Menampilkan informasi aplikasi."""
    return jsonify({
        "application": "Belajar DevSecOps Pipeline",
        "framework": "Flask",
        "version": "1.1.0",
        "revision": os.getenv("APP_REVISION", "local")
    }), 200


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000)
