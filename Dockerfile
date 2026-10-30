FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

ARG APP_REVISION=local
ENV APP_REVISION=${APP_REVISION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.revision=${APP_REVISION}

WORKDIR /app

# Menjalankan container dengan non-root user demi keamanan runtime
RUN useradd -u 1000 -m appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app.py wsgi.py ./
COPY --chown=appuser:appuser templates/ ./templates/
RUN mkdir /data && chown appuser:appuser /data

USER appuser
EXPOSE 5000

CMD ["gunicorn", "--bind=0.0.0.0:5000", "--workers=2", "--preload", "--access-logfile=-", "--error-logfile=-", "--worker-tmp-dir=/tmp", "wsgi:app"]
