"""Application configuration for the Vocal Separator backend."""

import logging
import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


# Load backend/.env before reading any configuration values.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# Redis connection settings used by Celery.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
	_redis_credentials = f":{quote(REDIS_PASSWORD, safe='')}@"
else:
	_redis_credentials = ""

REDIS_URL = (
	f"redis://{_redis_credentials}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)


# Celery settings for background separation tasks.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_SERIALIZER = os.getenv("CELERY_TASK_SERIALIZER", "json")
CELERY_RESULT_SERIALIZER = os.getenv("CELERY_RESULT_SERIALIZER", "json")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600"))
CELERY_TASK_SOFT_TIME_LIMIT = int(
	os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "3300")
)


# Persistent directories for uploaded files and separated audio tracks.
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", BASE_DIR / "uploads"))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "outputs"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# Development frontend origins. Override with a comma-separated .env value.
_cors_origins = os.getenv(
	"CORS_ORIGINS",
	"http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]


# Spleeter model that produces vocals and accompaniment stems.
SPLEETER_MODEL = os.getenv("SPLEETER_MODEL", "2stems")
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "192k")


# Accepted audio formats and maximum upload size (500 MB by default).
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# Basic application logging; LOG_LEVEL can be changed through .env.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
	level=getattr(logging, LOG_LEVEL, logging.INFO),
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
LOGGER = logging.getLogger("vocal_separator")
