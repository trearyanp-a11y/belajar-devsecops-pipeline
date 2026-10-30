"""Entrypoint Gunicorn: siapkan database sebelum menerima permintaan."""

from app import app, init_db

__all__ = ["app"]

if not app.secret_key or len(app.secret_key) < 32:
    raise RuntimeError("Set SECRET_KEY acak minimal 32 karakter melalui Secret flask-session")

init_db()
