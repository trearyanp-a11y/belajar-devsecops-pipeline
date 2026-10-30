"""Portal autentikasi dan game Pac-Man dengan SQLite persisten."""

from contextlib import closing
from datetime import timedelta
import math
import os
from pathlib import Path
import secrets
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["DATABASE"] = os.getenv("DATABASE_PATH", "users.db")
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=16 * 1024,
)


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

        conn.execute(
            """CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.commit()


@app.before_request
def protect_requests():
    """Wajibkan login untuk game/API dan CSRF untuk perubahan data."""
    if request.endpoint in {"game", "add_score", "leaderboard", "search_score", "logout"}:
        if not session.get("username"):
            if request.path.startswith("/api/"):
                return jsonify(message="Sesi berakhir. Silakan login kembali."), 401
            return redirect(url_for("index"))
    if request.method == "POST":
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected.encode(), token.encode()):
            if request.path.startswith("/api/"):
                return jsonify(message="Formulir kedaluwarsa. Muat ulang halaman."), 400
            return render_template(
                "index.html", message="Formulir kedaluwarsa. Silakan coba lagi."
            ), 400
    return None


@app.context_processor
def template_context():
    """Sediakan token formulir dan identitas pemain kepada template."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"], "player": session.get("username")}


@app.after_request
def response_headers(response):
    """Cegah cache halaman akun dan batasi sumber konten ke aplikasi ini."""
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    """Validasi akun, buat session baru dan arahkan pemain ke game."""
    if session.get("username"):
        return redirect(url_for("game"))
    message = None

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
            session.clear()
            session.permanent = True
            session["username"] = username
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("game"))
        message = "Login Gagal! Kredensial tidak valid."

    return render_template("index.html", message=message)


@app.get("/game")
def game():
    """Tampilkan arena Pac-Man setelah guard memverifikasi session."""
    return render_template("game.html")


@app.post("/logout")
def logout():
    """Hapus session dan kembalikan pemain ke portal."""
    session.clear()
    return redirect(url_for("index"))


@app.post("/api/score")
def add_score():
    """Simpan skor valid atas nama akun yang terautentikasi."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(message="Data skor tidak valid."), 400
    score = payload.get("score")
    duration = payload.get("duration_seconds")
    valid_score = (isinstance(score, int) and not isinstance(score, bool)
                   and 0 <= score <= 10_000_000)
    valid_duration = (isinstance(duration, (int, float)) and not isinstance(duration, bool)
                      and 0 <= duration <= 86_400 and math.isfinite(duration))
    if not valid_score or not valid_duration:
        return jsonify(message="Skor atau durasi tidak valid."), 400
    with closing(get_db_connection()) as conn:
        cursor = conn.execute(
            "INSERT INTO scores (player_name, score, duration_seconds) VALUES (?, ?, ?)",
            (session["username"], score, round(duration, 2)),
        )
        conn.commit()
        score_id = cursor.lastrowid
    return jsonify(status="success", message="Skor tersimpan!", id=score_id), 201


@app.get("/api/leaderboard")
def leaderboard():
    """Ambil lima skor terbaik dengan urutan yang stabil."""
    with closing(get_db_connection()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM scores ORDER BY score DESC, duration_seconds ASC, id ASC LIMIT 5"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/search")
def search_score():
    """Cari nama akun secara tepat menggunakan parameterized SQL."""
    player_name = request.args.get("player_name", "").strip()
    with closing(get_db_connection()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM scores WHERE player_name = ? "
            "ORDER BY score DESC, duration_seconds ASC, id ASC LIMIT 10",
            (player_name,),
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/health", methods=["GET"])
def health():
    """Readiness memeriksa database yang sudah ada tanpa membuat DB kosong."""
    database_uri = Path(app.config["DATABASE"]).resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(database_uri, uri=True, timeout=1)) as conn:
            conn.execute("SELECT username FROM users LIMIT 1").fetchone()
            conn.execute("SELECT id FROM scores LIMIT 1").fetchone()
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
        "application": "Pac-Man Portal DevSecOps",
        "framework": "Flask",
        "version": "1.2.0",
        "revision": os.getenv("APP_REVISION", "local")
    }), 200


if __name__ == "__main__":
    if not app.secret_key or len(app.secret_key) < 32:
        raise RuntimeError("Set SECRET_KEY acak minimal 32 karakter")
    init_db()
    app.run(host="127.0.0.1", port=5000)
