"""Entrypoint Gunicorn: siapkan database sebelum menerima permintaan."""

from app import app, init_db

__all__ = ["app"]

init_db()
