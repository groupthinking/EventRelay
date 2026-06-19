# Clean-spine service image (Cloud Run target).
# Single service, single entrypoint. Supersedes the repo-root Dockerfile and
# Dockerfile.cloudrun once the spine takes over.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Minimal runtime deps for the spine. Pinned floors only; the legacy
# requirements.txt (yt-dlp, opencv, gcloud SDKs, etc.) is not inherited.
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.24.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "sqlalchemy>=2.0.0" \
    "asyncpg>=0.29.0" \
    "youtube-transcript-api>=1.0.0" \
    "google-genai>=1.0.0"

COPY service /srv/service

EXPOSE 8080
# Cloud Run provides $PORT; default to 8080 locally.
CMD ["sh", "-c", "uvicorn service.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
