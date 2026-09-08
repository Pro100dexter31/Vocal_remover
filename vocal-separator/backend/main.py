"""FastAPI application for uploading and downloading separated audio."""

import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from .config import (
	ALLOWED_EXTENSIONS,
	AUDIO_OUTPUT_FORMAT,
	CORS_ORIGINS,
	MAX_FILE_SIZE_BYTES,
	OUTPUTS_DIR,
	UPLOADS_DIR,
)
from .tasks import celery_app, process_audio_task


LOGGER = logging.getLogger(__name__)


class UploadResponse(BaseModel):
	task_id: str
	status: str
	message: str


class StatusResponse(BaseModel):
	task_id: str
	status: str
	progress: int = 0
	vocals_url: str | None = None
	accompaniment_url: str | None = None
	error: str | None = None


def _status_payload(task_id: str, result: AsyncResult) -> dict[str, Any]:
	info = result.info if isinstance(result.info, dict) else {}
	state = result.state
	payload: dict[str, Any] = {
		"task_id": task_id,
		"status": "PROCESSING" if state in ("STARTED", "RETRY") else state,
		"progress": int(info.get("progress", 0)),
		"vocals_url": info.get("vocals_url"),
		"accompaniment_url": info.get("accompaniment_url"),
		"error": info.get("error"),
	}
	if state == "SUCCESS":
		payload["progress"] = 100
	if state == "FAILURE":
		payload["error"] = str(result.result)
	return payload


@asynccontextmanager
async def lifespan(_: FastAPI):
	LOGGER.info("Vocal Separator API starting")
	UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
	OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
	try:
		yield
	finally:
		LOGGER.info("Vocal Separator API shutting down")


app = FastAPI(
	title="Vocal Separator API",
	description="Separate vocals from accompaniment in uploaded audio files.",
	version="1.0.0",
	lifespan=lifespan,
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
	LOGGER.exception("Unhandled API error: %s", exc)
	return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
async def health_check() -> dict[str, str]:
	return {"status": "healthy", "service": "vocal-separator"}


@app.post("/api/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio(file: UploadFile = File(...)) -> UploadResponse:
	filename = Path(file.filename or "").name
	extension = Path(filename).suffix.lower()
	if not filename or extension not in ALLOWED_EXTENSIONS:
		raise HTTPException(
			status_code=400,
			detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
		)

	task_id = str(uuid4())
	destination = UPLOADS_DIR / f"{task_id}_{filename}"
	total_size = 0
	try:
		with destination.open("wb") as output_file:
			while chunk := await file.read(1024 * 1024):
				total_size += len(chunk)
				if total_size > MAX_FILE_SIZE_BYTES:
					raise HTTPException(status_code=413, detail="File exceeds the 500 MB limit")
				output_file.write(chunk)
		await file.close()
		process_audio_task.apply_async(args=[task_id, str(destination)], task_id=task_id)
	except HTTPException:
		destination.unlink(missing_ok=True)
		raise
	except Exception as exc:
		destination.unlink(missing_ok=True)
		LOGGER.exception("Upload failed for %s: %s", task_id, exc)
		raise HTTPException(status_code=500, detail="Could not queue audio processing") from exc

	return UploadResponse(
		task_id=task_id,
		status="PENDING",
		message="Audio uploaded and queued for separation",
	)


@app.get("/api/status/{task_id}", response_model=StatusResponse)
async def task_status(task_id: str) -> StatusResponse:
	result = AsyncResult(task_id, app=celery_app)
	return StatusResponse(**_status_payload(task_id, result))


@app.get("/api/download/{task_id}/{file_type}")
async def download_audio(
	task_id: str,
	file_type: Literal["vocals", "accompaniment"],
) -> FileResponse:
	# Optimization: Try MP3 first (smaller files), fallback to WAV for backward compatibility
	if AUDIO_OUTPUT_FORMAT == "mp3":
		file_path = OUTPUTS_DIR / task_id / f"{file_type}.mp3"
		media_type = "audio/mpeg"
		filename = f"{file_type}.mp3"
	else:
		file_path = OUTPUTS_DIR / task_id / f"{file_type}.wav"
		media_type = "audio/wav"
		filename = f"{file_type}.wav"

	# Fallback: check other format if file not found
	if not file_path.is_file():
		alt_format = "wav" if AUDIO_OUTPUT_FORMAT == "mp3" else "mp3"
		alt_path = OUTPUTS_DIR / task_id / f"{file_type}.{alt_format}"
		if alt_path.is_file():
			file_path = alt_path
			media_type = "audio/wav" if alt_format == "wav" else "audio/mpeg"
			filename = f"{file_type}.{alt_format}"
		else:
			raise HTTPException(status_code=404, detail="Audio output not found")

	return FileResponse(
		path=file_path,
		media_type=media_type,
		filename=filename,
		headers={"Content-Disposition": f'attachment; filename="{filename}"'},
	)
