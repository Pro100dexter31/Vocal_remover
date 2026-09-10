FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_HOME=/app/.cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 curl unzip \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app app

# Deno: yt-dlp (Feature 7) needs a JS runtime to solve YouTube's signature
# challenges - without one, extraction fails with a misleading "video
# unavailable" error instead of the real cause.
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/install.sh | sh

COPY backend/requirements.txt backend/requirements-dev.txt /app/backend/

# On arm64 the default PyPI wheels are already CPU-only; on amd64 the dedicated
# CPU index avoids pulling in the multi-gigabyte CUDA runtime.
ARG TARGETARCH
RUN pip install --upgrade pip \
    && if [ "$TARGETARCH" = "arm64" ]; then \
         pip install torch==2.5.1 torchaudio==2.5.1; \
       else \
         pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 torchaudio==2.5.1; \
       fi \
    && grep -Ev '^(torch|torchaudio)==' /app/backend/requirements.txt > /tmp/requirements-rest.txt \
    && pip install -r /tmp/requirements-rest.txt \
    && pip install -r /app/backend/requirements-dev.txt \
    && rm /tmp/requirements-rest.txt

# Bake the pretrained model into the image so the first job does not wait on a download.
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

COPY backend /app/backend
RUN mkdir -p /app/backend/uploads /app/backend/outputs \
    && chown -R app:app /app

USER app
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
