# syntax=docker/dockerfile:1

FROM python:3.13-slim

# Pillow needs no build tools with wheels, but keep the image honest about
# what it has: no compiler, no cache, nothing to exploit that we don't use.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY web ./web
COPY main.py ./

# Writable state lives here. Mount a persistent disk at /data in production or
# every balance, referral and generated image is lost on redeploy.
ENV MEDIA_DIR=/data/media \
    APP_DB=/data/app.db \
    ANALYTICS_DB=/data/analytics.db
RUN mkdir -p /data/media

EXPOSE 8000

# $PORT is injected by the platform; 8000 is the local default.
CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
