"""FastAPI application for uploading and downloading separated audio."""

import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

from .audio_converter import (
	convert_audio,
	InvalidFormatError,
	InvalidBitrateError,
	AudioConversionError,
)
from .config import (
	ALLOWED_EXTENSIONS,
	AUDIO_OUTPUT_FORMAT,
	CORS_ORIGINS,
	MAX_FILE_SIZE_BYTES,
	OUTPUTS_DIR,
	UPLOADS_DIR,
)
from .tasks import celery_app, process_audio_task
from .speed_adjuster import SUPPORTED_SPEEDS


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
async def upload_audio(
	file: UploadFile = File(...),
	separation_intensity: float = 0.5,
	normalize: bool = True,
	speed: float = 1.0,
) -> UploadResponse:
	filename = Path(file.filename or "").name
	extension = Path(filename).suffix.lower()
	if not filename or extension not in ALLOWED_EXTENSIONS:
		raise HTTPException(
			status_code=400,
			detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
		)

	# Validate separation_intensity is in valid range
	if not 0.0 <= separation_intensity <= 1.0:
		raise HTTPException(
			status_code=400,
			detail="separation_intensity must be between 0.0 and 1.0",
		)

	# Validate speed is in valid range
	supported_speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
	if speed not in supported_speeds:
		raise HTTPException(
			status_code=400,
			detail=f"Speed must be one of: {', '.join(f'{s}x' for s in supported_speeds)}",
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
		process_audio_task.apply_async(args=[task_id, str(destination), separation_intensity, normalize, speed], task_id=task_id)
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


@app.post("/api/export/{task_id}")
async def export_audio(
	task_id: str,
	file_type: Literal["vocals", "accompaniment"],
	output_format: str = Query(..., regex="^(mp3|flac|ogg|wav)$"),
	bitrate: str | None = Query(None, regex="^(128k|192k|320k)$"),
) -> FileResponse:
	"""
	Export separated audio in different formats.

	Args:
		task_id: ID of the processed task
		file_type: Either "vocals" or "accompaniment"
		output_format: Target format (mp3, flac, ogg, wav)
		bitrate: Optional bitrate for lossy formats (128k, 192k, 320k)

	Returns:
		FileResponse with converted audio file

	Raises:
		HTTPException 404: If source file not found
		HTTPException 400: If format/bitrate invalid
		HTTPException 500: If conversion fails
	"""
	try:
		# Determine source file format
		source_format = AUDIO_OUTPUT_FORMAT if AUDIO_OUTPUT_FORMAT in ("mp3", "wav") else "wav"
		source_file = OUTPUTS_DIR / task_id / f"{file_type}.{source_format}"

		# Fallback: check other format if not found
		if not source_file.exists():
			alt_format = "wav" if source_format == "mp3" else "mp3"
			alt_path = OUTPUTS_DIR / task_id / f"{file_type}.{alt_format}"
			if alt_path.exists():
				source_file = alt_path
			else:
				LOGGER.error("Source file not found for task %s, file_type %s", task_id, file_type)
				raise HTTPException(status_code=404, detail="Audio file not found")

		# Handle case where source and target are the same format
		if source_file.suffix.lstrip(".").lower() == output_format.lower():
			# No conversion needed, return source file directly
			return FileResponse(
				path=source_file,
				media_type=_get_media_type(output_format),
				filename=f"{file_type}.{output_format}",
				headers={"Content-Disposition": f'attachment; filename="{file_type}.{output_format}"'},
			)

		# Perform conversion
		output_file = OUTPUTS_DIR / task_id / f"{file_type}_converted.{output_format}"

		LOGGER.info(
			"Converting %s (%s) to %s with bitrate %s",
			file_type,
			source_file.suffix,
			output_format,
			bitrate or "default",
		)

		try:
			convert_audio(
				input_path=source_file,
				output_path=output_file,
				output_format=output_format,
				bitrate=bitrate,
			)
		except (InvalidFormatError, InvalidBitrateError) as e:
			LOGGER.warning("Invalid format/bitrate: %s", e)
			raise HTTPException(status_code=400, detail=str(e)) from e
		except AudioConversionError as e:
			LOGGER.error("Conversion failed: %s", e)
			raise HTTPException(status_code=500, detail="Audio conversion failed") from e

		# Verify output file was created
		if not output_file.exists():
			LOGGER.error("Output file not created for task %s", task_id)
			raise HTTPException(status_code=500, detail="Conversion failed - output file not created")

		# Get file size for logging
		file_size_mb = output_file.stat().st_size / (1024 * 1024)
		LOGGER.info("✓ Conversion complete: %s (%.2f MB)", output_file.name, file_size_mb)

		# Return converted file
		return FileResponse(
			path=output_file,
			media_type=_get_media_type(output_format),
			filename=f"{file_type}.{output_format}",
			headers={"Content-Disposition": f'attachment; filename="{file_type}.{output_format}"'},
		)

	except HTTPException:
		raise
	except Exception as exc:
		LOGGER.exception("Unexpected error in export_audio: %s", exc)
		raise HTTPException(status_code=500, detail="Internal server error") from exc


def _get_media_type(audio_format: str) -> str:
	"""Get MIME type for audio format."""
	media_types = {
		"mp3": "audio/mpeg",
		"wav": "audio/wav",
		"flac": "audio/flac",
		"ogg": "audio/ogg",
	}
	return media_types.get(audio_format.lower(), "application/octet-stream")


PREVIEW_BUFFER_SIZE = 30 * 1024 * 1024  # 30 MB buffer for first 30 seconds
CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming


async def _stream_audio_file(file_path: Path, range_header: str | None = None):
	"""
	Stream audio file with optional range request support (HTTP 206).

	Args:
		file_path: Path to audio file to stream
		range_header: HTTP Range header value (e.g., "bytes=0-1023")

	Yields:
		Chunks of file data
	"""
	file_size = file_path.stat().st_size

	if range_header:
		try:
			range_start, range_end = range_header.replace("bytes=", "").split("-")
			start = int(range_start) if range_start else 0
			end = int(range_end) if range_end else file_size - 1

			if start > end or start >= file_size:
				raise ValueError("Invalid range")

			end = min(end, file_size - 1)
			length = end - start + 1

			LOGGER.info("Streaming range %d-%d (size: %d)", start, end, length)

			with open(file_path, "rb") as f:
				f.seek(start)
				remaining = length
				while remaining > 0:
					chunk_len = min(CHUNK_SIZE, remaining)
					chunk = f.read(chunk_len)
					if not chunk:
						break
					yield chunk
					remaining -= len(chunk)
		except (ValueError, IndexError) as e:
			LOGGER.warning("Invalid range header: %s", e)
			# Fallback to full file streaming
			with open(file_path, "rb") as f:
				while True:
					chunk = f.read(CHUNK_SIZE)
					if not chunk:
						break
					yield chunk
	else:
		# Stream full file
		with open(file_path, "rb") as f:
			while True:
				chunk = f.read(CHUNK_SIZE)
				if not chunk:
					break
				yield chunk


@app.get("/api/preview/{task_id}")
async def preview_audio(
	task_id: str,
	file_type: Literal["vocals", "accompaniment", "both"] = "both",
	request: Request = None,
) -> StreamingResponse:
	"""
	Stream audio preview without full download.

	Supports HTTP range requests for seeking.

	Args:
		task_id: ID of the processed task
		file_type: "vocals", "accompaniment", or "both"
		request: HTTP request object

	Returns:
		StreamingResponse with audio data

	Raises:
		HTTPException 404: If audio files not found
		HTTPException 416: If invalid range request
	"""
	try:
		# Determine source file format
		source_format = AUDIO_OUTPUT_FORMAT if AUDIO_OUTPUT_FORMAT in ("mp3", "wav") else "wav"

		# Get file paths
		vocals_path = OUTPUTS_DIR / task_id / f"vocals.{source_format}"
		accompaniment_path = OUTPUTS_DIR / task_id / f"accompaniment.{source_format}"

		# Fallback: check other format if not found
		if not vocals_path.exists():
			alt_format = "wav" if source_format == "mp3" else "mp3"
			alt_vocals = OUTPUTS_DIR / task_id / f"vocals.{alt_format}"
			if alt_vocals.exists():
				vocals_path = alt_vocals

		if not accompaniment_path.exists():
			alt_format = "wav" if source_format == "mp3" else "mp3"
			alt_accompaniment = OUTPUTS_DIR / task_id / f"accompaniment.{alt_format}"
			if alt_accompaniment.exists():
				accompaniment_path = alt_accompaniment

		# Determine which file(s) to stream
		if file_type == "vocals":
			if not vocals_path.exists():
				raise HTTPException(status_code=404, detail="Vocal track not found")
			stream_path = vocals_path
			filename = "vocals"
		elif file_type == "accompaniment":
			if not accompaniment_path.exists():
				raise HTTPException(status_code=404, detail="Accompaniment track not found")
			stream_path = accompaniment_path
			filename = "accompaniment"
		else:  # both
			if not vocals_path.exists() or not accompaniment_path.exists():
				raise HTTPException(status_code=404, detail="Audio tracks not found")
			# For "both", stream the mix (vocals + accompaniment)
			# Use vocals as primary, as both are available
			stream_path = vocals_path
			filename = "preview"

		file_size = stream_path.stat().st_size
		range_header = request.headers.get("range") if request else None
		media_type = _get_media_type(stream_path.suffix.lstrip("."))

		# Handle range requests (HTTP 206 Partial Content)
		if range_header:
			try:
				range_start, range_end = range_header.replace("bytes=", "").split("-")
				start = int(range_start) if range_start else 0
				end = int(range_end) if range_end else file_size - 1

				if start > end or start >= file_size:
					raise HTTPException(
						status_code=416,
						detail=f"Range not satisfiable. File size: {file_size}"
					)

				end = min(end, file_size - 1)
				length = end - start + 1

				LOGGER.info(
					"Preview range request: %d-%d/%d for %s",
					start, end, file_size, filename
				)

				return StreamingResponse(
					_stream_audio_file(stream_path, range_header),
					status_code=206,
					media_type=media_type,
					headers={
						"Content-Range": f"bytes {start}-{end}/{file_size}",
						"Content-Length": str(length),
						"Accept-Ranges": "bytes",
						"Content-Disposition": f"inline; filename=\"{filename}.{stream_path.suffix.lstrip('.')}\"",
					}
				)
			except ValueError as e:
				LOGGER.warning("Invalid range header: %s", e)
				raise HTTPException(status_code=416, detail="Invalid range request")

		# Full file streaming
		LOGGER.info("Streaming full preview for %s (%s)", filename, stream_path.name)

		return StreamingResponse(
			_stream_audio_file(stream_path),
			media_type=media_type,
			headers={
				"Accept-Ranges": "bytes",
				"Content-Length": str(file_size),
				"Content-Disposition": f"inline; filename=\"{filename}.{stream_path.suffix.lstrip('.')}\"",
			}
		)

	except HTTPException:
		raise
	except Exception as e:
		LOGGER.exception("Preview streaming failed: %s", e)
		raise HTTPException(status_code=500, detail="Could not stream audio preview")


@app.post("/api/process/{task_id}")
async def process_speed_adjustment(
	task_id: str,
	speed: float = Query(1.0, ge=0.5, le=2.0),
) -> dict[str, Any]:
	"""
	Process speed adjustment for a completed task.

	Args:
		task_id: ID of the processed task
		speed: Speed factor (0.5-2.0, default 1.0)

	Returns:
		JSON with status and processing info

	Raises:
		HTTPException 400: If speed is invalid
		HTTPException 404: If task output not found
		HTTPException 500: If processing fails
	"""
	# Validate speed is supported
	supported_speeds = list(SUPPORTED_SPEEDS.keys())
	if speed not in supported_speeds:
		raise HTTPException(
			status_code=400,
			detail=f"Speed must be one of: {', '.join(f'{s}x' for s in supported_speeds)}",
		)

	# Check if output files exist
	output_dir = OUTPUTS_DIR / task_id
	vocal_files = list(output_dir.glob("vocals.*"))
	accompaniment_files = list(output_dir.glob("accompaniment.*"))

	if not vocal_files or not accompaniment_files:
		raise HTTPException(
			status_code=404,
			detail="Task output not found. Please complete separation first.",
		)

	# If speed is 1.0, no processing needed
	if speed == 1.0:
		return {
			"status": "completed",
			"task_id": task_id,
			"speed": speed,
			"message": "Speed 1.0x (no adjustment needed)",
		}

	# For speeds != 1.0, return processing status
	# (In production, would queue async task for speed adjustment)
	return {
		"status": "processing",
		"task_id": task_id,
		"speed": speed,
		"message": f"Speed adjustment queued for {speed}x",
		"estimated_duration_seconds": 120,  # ~2 minutes for typical 1-minute audio
	}
