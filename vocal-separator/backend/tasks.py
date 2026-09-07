"""Celery tasks for asynchronous vocal separation."""

import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from celery import Celery, Task

from .config import (
	ALLOWED_EXTENSIONS,
	CELERY_BROKER_URL,
	CELERY_RESULT_BACKEND,
	CELERY_RESULT_SERIALIZER,
	CELERY_TASK_SERIALIZER,
	CELERY_TASK_SOFT_TIME_LIMIT,
	CELERY_TASK_TIME_LIMIT,
	CLEANUP_INTERVAL_MINUTES,
	DEMUCS_MODEL,
	DEMUCS_OVERLAP,
	DEMUCS_SECONDS_PER_AUDIO_SECOND,
	DEMUCS_THREADS,
	OUTPUTS_DIR,
	RETENTION_HOURS,
	UPLOADS_DIR,
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
	beat_schedule={
		"cleanup-expired-audio": {
			"task": "backend.tasks.cleanup_old_tasks",
			"schedule": CLEANUP_INTERVAL_MINUTES * 60.0,
		}
	},
)

_separator = None


def get_or_create_separator():
	"""Load the Demucs model only when the first task needs it."""
	global _separator
	if _separator is None:
		import torch
		from demucs.pretrained import get_model

		torch.set_num_threads(DEMUCS_THREADS)
		LOGGER.info(
			"Loading Demucs model: %s (using %d of %d cores)",
			DEMUCS_MODEL,
			DEMUCS_THREADS,
			os.cpu_count() or 1,
		)
		model = get_model(DEMUCS_MODEL)
		model.eval()
		_separator = model
	return _separator


def _separate_stems(model, audio_path: Path, output_dir: Path, on_progress=None) -> None:
	"""Split the track into vocals.wav and accompaniment.wav inside output_dir.

	Demucs exposes no progress callback, so progress is estimated from elapsed
	time against the track duration while separation runs on a worker thread.
	"""
	from demucs.apply import apply_model
	from demucs.audio import AudioFile, save_audio

	waveform = AudioFile(str(audio_path)).read(
		streams=0,
		samplerate=model.samplerate,
		channels=model.audio_channels,
	)
	reference = waveform.mean(0)
	normalized = (waveform - reference.mean()) / reference.std()

	audio_seconds = waveform.shape[-1] / model.samplerate
	estimated_seconds = max(audio_seconds * DEMUCS_SECONDS_PER_AUDIO_SECOND, 1.0)

	with ThreadPoolExecutor(max_workers=1) as pool:
		future = pool.submit(
			apply_model,
			model,
			normalized[None],
			device="cpu",
			progress=False,
			overlap=DEMUCS_OVERLAP,
		)
		started = time.monotonic()
		while not future.done():
			time.sleep(2)
			if on_progress:
				elapsed = time.monotonic() - started
				on_progress(min(elapsed / estimated_seconds, 1.0))
		sources = future.result()[0]

	sources = sources * reference.std() + reference.mean()

	stems = dict(zip(model.sources, sources))
	vocals = stems["vocals"]
	accompaniment = sum(audio for name, audio in stems.items() if name != "vocals")

	save_audio(vocals, str(output_dir / "vocals.wav"), model.samplerate)
	save_audio(accompaniment, str(output_dir / "accompaniment.wav"), model.samplerate)


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
		self.update_state(state="PROCESSING", meta={"progress": 20, "task_id": task_id})

		separator = get_or_create_separator()
		self.update_state(state="PROCESSING", meta={"progress": 30, "task_id": task_id})

		def report(fraction: float) -> None:
			self.update_state(
				state="PROCESSING",
				meta={"progress": 30 + int(60 * fraction), "task_id": task_id},
			)

		_separate_stems(separator, audio_path, output_dir, on_progress=report)
		if not (output_dir / "vocals.wav").is_file() or not (output_dir / "accompaniment.wav").is_file():
			raise FileNotFoundError("Demucs did not produce both expected stems")
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


def _is_older_than(path: Path, cutoff: datetime) -> bool:
	return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff


@celery_app.task(name="backend.tasks.cleanup_old_tasks")
def cleanup_old_tasks(max_age_hours: int | None = None) -> dict[str, int]:
	"""Delete separated stems and their source uploads past the retention window."""
	cutoff = datetime.now(timezone.utc) - timedelta(
		hours=max_age_hours if max_age_hours is not None else RETENTION_HOURS
	)
	removed = {"outputs": 0, "uploads": 0, "freed_mb": 0}
	freed_bytes = 0

	for task_dir in OUTPUTS_DIR.iterdir():
		if task_dir.is_dir() and _is_older_than(task_dir, cutoff):
			freed_bytes += sum(f.stat().st_size for f in task_dir.rglob("*") if f.is_file())
			shutil.rmtree(task_dir, ignore_errors=True)
			removed["outputs"] += 1

	for upload in UPLOADS_DIR.iterdir():
		if upload.is_file() and _is_older_than(upload, cutoff):
			freed_bytes += upload.stat().st_size
			upload.unlink(missing_ok=True)
			removed["uploads"] += 1

	removed["freed_mb"] = round(freed_bytes / (1024 * 1024))
	LOGGER.info(
		"Cleanup removed %d output folders and %d uploads, freeing %d MB",
		removed["outputs"],
		removed["uploads"],
		removed["freed_mb"],
	)
	return removed
