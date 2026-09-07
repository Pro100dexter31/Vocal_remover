"""Celery tasks for asynchronous vocal separation."""

import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from celery import Celery, Task

from .config import (
	ALLOWED_EXTENSIONS,
	AUDIO_BITRATE,
	CELERY_BROKER_URL,
	CELERY_RESULT_BACKEND,
	CELERY_RESULT_SERIALIZER,
	CELERY_TASK_SERIALIZER,
	CELERY_TASK_SOFT_TIME_LIMIT,
	CELERY_TASK_TIME_LIMIT,
	OUTPUTS_DIR,
	SPLEETER_MODEL,
)


LOGGER = logging.getLogger(__name__)

celery_app = Celery(
	"vocal_separator",
	broker=CELERY_BROKER_URL,
	backend=CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
	task_serializer=CELERY_TASK_SERIALIZER,
	result_serializer=CELERY_RESULT_SERIALIZER,
	accept_content=["json"],
	task_track_started=True,
	task_time_limit=CELERY_TASK_TIME_LIMIT,
	task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
	result_expires=86400,
)

_separator = None


def get_or_create_separator():
	"""Load the Spleeter model only when the first task needs it."""
	global _separator
	if _separator is None:
		from spleeter.separator import Separator

		LOGGER.info("Loading Spleeter model: %s", SPLEETER_MODEL)
		_separator = Separator(SPLEETER_MODEL)
	return _separator


class CallbackTask(Task):
	"""Log task lifecycle events while keeping failures serializable."""

	def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
		LOGGER.warning("Task %s retrying: %s", task_id, exc)
		super().on_retry(exc, task_id, args, kwargs, einfo)

	def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
		LOGGER.exception("Task %s failed: %s", task_id, exc)
		super().on_failure(exc, task_id, args, kwargs, einfo)

	def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
		LOGGER.info("Task %s completed successfully", task_id)
		super().on_success(retval, task_id, args, kwargs)


def _validate_audio_file(file_path: Path) -> None:
	if not file_path.is_file():
		raise FileNotFoundError(f"Audio file does not exist: {file_path}")
	if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
		raise ValueError(f"Unsupported audio extension: {file_path.suffix}")


@celery_app.task(
	bind=True,
	base=CallbackTask,
	name="backend.tasks.process_audio_task",
	max_retries=2,
)
def process_audio_task(self, task_id: str, file_path: str) -> dict[str, Any]:
	"""Separate one uploaded file into vocals and accompaniment WAV files."""
	output_dir = OUTPUTS_DIR / task_id
	try:
		self.update_state(state="PROCESSING", meta={"progress": 10, "task_id": task_id})
		audio_path = Path(file_path).resolve()
		_validate_audio_file(audio_path)

		output_dir.mkdir(parents=True, exist_ok=True)
		self.update_state(state="PROCESSING", meta={"progress": 40, "task_id": task_id})

		separator = get_or_create_separator()
		temp_dir = output_dir / "spleeter"
		separator.separate_to_file(
			str(audio_path),
			str(temp_dir),
			codec="wav",
			bitrate=AUDIO_BITRATE,
			synchronous=True,
		)
		self.update_state(state="PROCESSING", meta={"progress": 70, "task_id": task_id})

		stem_dir = temp_dir / audio_path.stem
		vocals_source = stem_dir / "vocals.wav"
		accompaniment_source = stem_dir / "accompaniment.wav"
		if not vocals_source.is_file() or not accompaniment_source.is_file():
			raise FileNotFoundError("Spleeter did not produce both expected stems")

		shutil.copy2(vocals_source, output_dir / "vocals.wav")
		shutil.copy2(accompaniment_source, output_dir / "accompaniment.wav")
		shutil.rmtree(temp_dir, ignore_errors=True)
		self.update_state(state="PROCESSING", meta={"progress": 95, "task_id": task_id})

		result = {
			"task_id": task_id,
			"status": "SUCCESS",
			"progress": 100,
			"vocals_url": f"/api/download/{task_id}/vocals",
			"accompaniment_url": f"/api/download/{task_id}/accompaniment",
		}
		self.update_state(state="SUCCESS", meta=result)
		return result
	except Exception as exc:
		LOGGER.exception("Audio processing failed for task %s", task_id)
		if self.request.retries < self.max_retries:
			raise self.retry(exc=exc, countdown=5)
		raise


@celery_app.task(name="backend.tasks.ping_task")
def ping_task() -> str:
	"""Simple worker health check."""
	return "pong"


@celery_app.task(name="backend.tasks.cleanup_old_tasks")
def cleanup_old_tasks(max_age_hours: int = 24) -> int:
	"""Remove output folders older than the configured retention window."""
	cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
	removed = 0
	for task_dir in OUTPUTS_DIR.iterdir():
		if not task_dir.is_dir():
			continue
		modified_at = datetime.fromtimestamp(task_dir.stat().st_mtime, timezone.utc)
		if modified_at < cutoff:
			shutil.rmtree(task_dir, ignore_errors=True)
			removed += 1
	LOGGER.info("Removed %d old task output folders", removed)
	return removed
