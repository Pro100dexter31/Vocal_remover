FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && grep -Ev '^(spleeter|torch)==' /app/backend/requirements.txt > /tmp/requirements-without-spleeter-torch.txt \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch==2.1.0 \
    && pip install -r /tmp/requirements-without-spleeter-torch.txt \
    && pip install --no-deps spleeter==2.4.0 \
    && rm /tmp/requirements-without-spleeter-torch.txt

COPY backend /app/backend
RUN mkdir -p /app/backend/uploads /app/backend/outputs \
    && chown -R app:app /app

USER app
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
