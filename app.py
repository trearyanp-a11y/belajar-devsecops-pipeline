"""Modul backend autentikasi Flask dengan antarmuka web interaktif."""

import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


def init_db():
    """Inisialisasi basis data dan membuat data pengguna awal."""
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT,
                password TEXT
            )
            """
        )

        cursor.execute(
            "SELECT 1 FROM users WHERE username = ?",
            ("admin",)
        )

        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("admin", "supersecret")
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

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()

            # Parameterized query untuk mencegah SQL Injection
            query = """
                SELECT * FROM users
                WHERE username = ? AND password = ?
            """
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

        if user:
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
    """Health check untuk memastikan aplikasi sedang berjalan."""
    return jsonify({
        "status": "ok",
        "service": "flask-auth-app"
    }), 200


@app.route("/about", methods=["GET"])
def about():
    """Menampilkan informasi aplikasi."""
    return jsonify({
        "application": "Belajar DevSecOps Pipeline",
        "framework": "Flask",
        "version": "1.0.0"
    }), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)  # nosemgrep
