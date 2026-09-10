# Single-container build for Hugging Face Spaces (Docker SDK).
# Runs redis + celery worker + uvicorn (FastAPI, which also serves the
# React build) under supervisord. Locally you still use docker-compose;
# this file is only for the Spaces deploy.

# --- Stage 1: build the React frontend -------------------------------------
FROM node:18-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: python runtime + redis + supervisord -----------------------
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_HOME=/app/.cache/torch \
    NUMBA_CACHE_DIR=/tmp/numba_cache \
    UPLOADS_DIR=/tmp/uploads \
    OUTPUTS_DIR=/tmp/outputs \
    REDIS_HOST=localhost \
    MODEL_IDLE_TIMEOUT_SECONDS=3600 \
    RETENTION_HOURS=1 \
    CLEANUP_INTERVAL_MINUTES=15 \
    MP3_BITRATE=128k \
    DEMUCS_OVERLAP=0.25

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         ffmpeg libsndfile1 curl unzip redis-server supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 app \
    && useradd -m -u 1000 -g app app

# Deno: yt-dlp needs a JS runtime for YouTube signature challenges.
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/install.sh | sh

COPY backend/requirements.txt /app/backend/requirements.txt
# On arm64 the default PyPI wheels are already CPU-only; on amd64 (Hugging Face
# build hosts) the dedicated CPU index avoids the multi-GB CUDA runtime.
ARG TARGETARCH
RUN pip install --upgrade pip \
    && if [ "$TARGETARCH" = "arm64" ]; then \
         pip install torch==2.5.1 torchaudio==2.5.1; \
       else \
         pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 torchaudio==2.5.1; \
       fi \
    && grep -Ev '^(torch|torchaudio)==' /app/backend/requirements.txt > /tmp/req.txt \
    && pip install -r /tmp/req.txt \
    && rm /tmp/req.txt

# Bake the pretrained model into the image so the first job does not wait on a download.
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

COPY backend /app/backend
COPY --from=frontend /fe/build /app/frontend_build
COPY supervisord.conf /app/supervisord.conf

RUN mkdir -p /tmp/uploads /tmp/outputs /tmp/numba_cache \
    && chown -R app:app /app /tmp/uploads /tmp/outputs /tmp/numba_cache

USER app
EXPOSE 7860

CMD ["supervisord", "-c", "/app/supervisord.conf"]
