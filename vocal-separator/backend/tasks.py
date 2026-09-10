"""Celery tasks for asynchronous vocal separation."""

import gc
import logging
import math
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psutil
from celery import Celery, Task

from .config import (
	ALLOWED_EXTENSIONS,
	AUDIO_OUTPUT_FORMAT,
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
	MODEL_IDLE_TIMEOUT_SECONDS,
	MP3_BITRATE,
	OUTPUTS_DIR,
	RETENTION_HOURS,
	UPLOADS_DIR,
	YOUTUBE_AUDIO_BITRATE_KBPS,
	YOUTUBE_DOWNLOAD_TIMEOUT_SECONDS,
)
from .volume_normalizer import normalize_audio_file, NormalizationError
from .speed_adjuster import adjust_speed, InvalidSpeedError, SpeedProcessingError
from .speed_cache import SpeedCache
from .pitch_shifter import adjust_pitch, InvalidSemitonesError, PitchProcessingError
from .waveform import generate_waveform_peaks, generate_waveform_peaks_streaming, save_waveform_data
from .youtube_extractor import (
	download_audio,
	YouTubeExtractionError,
	InvalidURLError,
	VideoTooLongError,
	VideoUnavailableError,
)
from .audio_trimmer import trim_audio, TrimError, InvalidTrimRangeError
from .audio_chunker import AudioChunker


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
	result_expires=3600,
	beat_schedule={
		"cleanup-expired-audio": {
			"task": "backend.tasks.cleanup_old_tasks",
			"schedule": CLEANUP_INTERVAL_MINUTES * 60.0,
		}
	},
)

_separator = None
_separator_last_used = None
_speed_cache = None
_pitch_cache = None


def get_speed_cache() -> SpeedCache:
	"""Get or create the speed adjustment cache."""
	global _speed_cache
	if _speed_cache is None:
		cache_dir = OUTPUTS_DIR / ".speed_cache"
		_speed_cache = SpeedCache(cache_dir)
	return _speed_cache


def get_pitch_cache() -> SpeedCache:
	"""Get or create the pitch adjustment cache (same key/value cache
	shape as speed, just a separate directory - see SpeedCache)."""
	global _pitch_cache
	if _pitch_cache is None:
		cache_dir = OUTPUTS_DIR / ".pitch_cache"
		_pitch_cache = SpeedCache(cache_dir)
	return _pitch_cache


def log_memory_usage(stage: str) -> None:
	"""Log current memory usage for performance monitoring."""
	try:
		process = psutil.Process()
		mem_info = process.memory_info()
		mem_mb = mem_info.rss / 1024 / 1024
		LOGGER.info("Memory usage [%s]: %.1f MB", stage, mem_mb)
	except Exception as e:
		LOGGER.warning("Could not log memory usage: %s", e)


def get_or_create_separator():
	"""Load the Demucs model only when the first task needs it.

	Unload if idle > MODEL_IDLE_TIMEOUT_SECONDS to save RAM (~80 MB).
	"""
	global _separator, _separator_last_used
	import torch
	from demucs.pretrained import get_model

	current_time = datetime.now()

	# Optimization: Unload model if idle > timeout (save 80 MB RAM)
	if _separator is not None and _separator_last_used:
		idle_seconds = (current_time - _separator_last_used).total_seconds()
		if idle_seconds > MODEL_IDLE_TIMEOUT_SECONDS:
			LOGGER.info(
				"Unloading model due to idle timeout (%.0f seconds > %d)",
				idle_seconds,
				MODEL_IDLE_TIMEOUT_SECONDS,
			)
			del _separator
			_separator = None
			gc.collect()

	if _separator is None:
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

	# Track last usage time for idle timeout
	_separator_last_used = current_time
	return _separator


def _separate_stems(model, audio_path: Path, output_dir: Path, separation_intensity: float = 0.5, on_progress=None) -> None:
	"""Split the track into vocals and accompaniment inside output_dir.

	For large files (>60s), uses chunked processing to reduce peak RAM.
	For normal files, processes entire track in memory.

	Args:
		separation_intensity: Controls vocal emphasis (0.0-1.0):
			- 0.0: instrumental only (vocals completely removed)
			- 0.5: balanced (50/50 original + separation)
			- 1.0: vocals maximized (original mix + vocal enhancement)

	Optimization: Saves output as MP3 (default) instead of WAV for 80% disk savings.
	"""
	from demucs.apply import apply_model
	from demucs.audio import AudioFile

	# Check if chunking needed
	chunker = AudioChunker(audio_path, chunk_duration_seconds=30.0, overlap_seconds=2.0)

	if chunker.should_chunk():
		LOGGER.info("Large audio detected (%.1f min) — using chunked separation", chunker.total_duration / 60.0)
		_separate_stems_chunked(model, audio_path, output_dir, separation_intensity, on_progress, chunker)
		return

	# Standard processing for normal-length audio
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

	# Apply separation intensity: blend original audio with separated stems based on intensity
	if separation_intensity != 0.5:
		intensity = max(0.0, min(1.0, separation_intensity))
		vocals = vocals * intensity + (waveform - accompaniment) * (1.0 - intensity)

	both_mix = vocals + accompaniment
	peak = float(both_mix.abs().max()) if hasattr(both_mix, "abs") else float(abs(both_mix).max())
	if peak > 1.0:
		both_mix = both_mix / peak

	# Save audio stems first, then generate waveforms from files (streaming, memory-efficient)
	_save_audio_stem(vocals, model.samplerate, output_dir, "vocals")
	_save_audio_stem(accompaniment, model.samplerate, output_dir, "accompaniment")
	_save_audio_stem(both_mix, model.samplerate, output_dir, "both")
	_save_audio_stem(waveform, model.samplerate, output_dir, "original")

	LOGGER.info("Outputs saved (%s): vocals, accompaniment, both, original", AUDIO_OUTPUT_FORMAT)

	# Feature 6: Generate waveforms from saved files via streaming (memory-efficient, no tensor copy)
	try:
		waveforms = {
			"original": generate_waveform_peaks_streaming(output_dir / f"original.{AUDIO_OUTPUT_FORMAT}"),
			"vocals": generate_waveform_peaks_streaming(output_dir / f"vocals.{AUDIO_OUTPUT_FORMAT}"),
			"accompaniment": generate_waveform_peaks_streaming(output_dir / f"accompaniment.{AUDIO_OUTPUT_FORMAT}"),
			"both": generate_waveform_peaks_streaming(output_dir / f"both.{AUDIO_OUTPUT_FORMAT}"),
		}
		save_waveform_data(output_dir, waveforms)
		gc.collect()
	except Exception as e:
		LOGGER.warning("Waveform data generation failed (continuing without it): %s", e)


def _separate_stems_chunked(model, audio_path: Path, output_dir: Path, separation_intensity: float, on_progress, chunker: AudioChunker) -> None:
	"""Process audio in chunks to reduce peak RAM for large files."""
	from demucs.apply import apply_model
	import numpy as np

	LOGGER.info("Chunked separation: %d chunks of ~%.0fs",
		(chunker.total_frames // chunker.step_frames) + 1,
		chunker.chunk_duration)

	all_chunks_vocals = []
	all_chunks_accompaniment = []
	all_chunks_both = []
	all_chunks_original = []

	chunk_count = 0
	for chunk, start_frame, end_frame in chunker.iter_chunks():
		chunk_count += 1

		reference = chunk.mean(axis=0) if chunk.ndim > 1 else chunk.mean()
		reference_std = 1.0
		if hasattr(reference, 'std'):
			reference_std = reference.std()
			if reference_std == 0:
				reference_std = 1.0

		normalized = (chunk - reference) / reference_std if reference_std > 0 else chunk

		if normalized.ndim == 1:
			normalized = normalized[np.newaxis, np.newaxis, :]
		elif normalized.ndim == 2:
			normalized = np.expand_dims(normalized.T, axis=0)
		else:
			normalized = np.expand_dims(normalized, axis=0)

		try:
			sources = apply_model(
				model,
				normalized,
				device="cpu",
				progress=False,
				overlap=DEMUCS_OVERLAP,
			)[0]
		except Exception as e:
			LOGGER.error("Chunk %d separation failed: %s", chunk_count, e)
			raise

		sources = sources * reference_std + reference
		if sources.ndim == 3:
			sources = sources[0]

		stems = dict(zip(model.sources, sources))
		chunk_vocals = stems["vocals"]
		chunk_accompaniment = sum(audio for name, audio in stems.items() if name != "vocals")

		if separation_intensity != 0.5:
			intensity = max(0.0, min(1.0, separation_intensity))
			chunk_vocals = chunk_vocals * intensity + (chunk - chunk_accompaniment) * (1.0 - intensity)

		all_chunks_vocals.append(chunk_vocals)
		all_chunks_accompaniment.append(chunk_accompaniment)
		all_chunks_original.append(chunk)

		both_mix = chunk_vocals + chunk_accompaniment
		peak = float(both_mix.abs().max()) if hasattr(both_mix, "abs") else float(abs(both_mix).max())
		if peak > 1.0:
			both_mix = both_mix / peak
		all_chunks_both.append(both_mix)

		if on_progress:
			on_progress(min((chunk_count * chunker.chunk_duration) / chunker.total_duration, 1.0))

		gc.collect()

	LOGGER.info("Blending %d chunks...", len(all_chunks_vocals))
	vocals_blended = all_chunks_vocals[0]
	accompaniment_blended = all_chunks_accompaniment[0]
	both_blended = all_chunks_both[0]
	original_blended = all_chunks_original[0]

	for i in range(1, len(all_chunks_vocals)):
		vocals_blended = AudioChunker.blend_chunks(vocals_blended, all_chunks_vocals[i], chunker.overlap_frames)
		accompaniment_blended = AudioChunker.blend_chunks(accompaniment_blended, all_chunks_accompaniment[i], chunker.overlap_frames)
		both_blended = AudioChunker.blend_chunks(both_blended, all_chunks_both[i], chunker.overlap_frames)
		original_blended = AudioChunker.blend_chunks(original_blended, all_chunks_original[i], chunker.overlap_frames)

	_save_audio_stem(vocals_blended, model.samplerate, output_dir, "vocals")
	_save_audio_stem(accompaniment_blended, model.samplerate, output_dir, "accompaniment")
	_save_audio_stem(both_blended, model.samplerate, output_dir, "both")
	_save_audio_stem(original_blended, model.samplerate, output_dir, "original")

	LOGGER.info("Chunked separation complete: %d chunks processed and blended", len(all_chunks_vocals))


def _save_audio_stem(audio, samplerate: int, output_dir: Path, name: str) -> None:
	"""
	Save one audio stem to output_dir/{name}.mp3 (falling back to .wav if
	MP3 conversion fails), via a temporary WAV write + pydub re-encode.

	Optimization: MP3 (default) saves ~80% disk space over WAV.
	"""
	from demucs.audio import save_audio

	temp_wav = output_dir / f"{name}_temp.wav"
	save_audio(audio, str(temp_wav), samplerate)

	if AUDIO_OUTPUT_FORMAT == "mp3":
		try:
			from pydub import AudioSegment

			AudioSegment.from_wav(str(temp_wav)).export(
				str(output_dir / f"{name}.mp3"),
				format="mp3",
				bitrate=MP3_BITRATE,
			)
			temp_wav.unlink(missing_ok=True)
			return
		except Exception as e:
			LOGGER.warning("MP3 conversion failed for %s, keeping WAV: %s", name, e)

	temp_wav.rename(output_dir / f"{name}.wav")


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


def _stretch_to_matching_format(source: Path, target: Path, speed: float) -> None:
	"""
	Time-stretch `source` to `speed`, writing the result to `target` in
	target's own format.

	soundfile (used by adjust_speed) can only write WAV/FLAC/OGG natively,
	not MP3. When the target is MP3 (or another format soundfile can't
	write), stretch into a temp WAV first, then re-encode via ffmpeg.
	"""
	target_format = target.suffix.lstrip(".").lower()
	if target_format in ("wav", "flac", "ogg"):
		adjust_speed(source, target, speed)
		return

	temp_wav = target.parent / f"{target.stem}_stretch_tmp.wav"
	try:
		adjust_speed(source, temp_wav, speed)
		from .audio_converter import convert_audio

		convert_audio(temp_wav, target, target_format, bitrate=None)
	finally:
		temp_wav.unlink(missing_ok=True)


def _apply_speed_adjustment(output_dir: Path, speed: float) -> None:
	"""
	Apply speed adjustment to separated stems (pitch-invariant time-stretching).

	Args:
		output_dir: Directory containing vocal and accompaniment files
		speed: Speed factor (0.5-2.0)

	Raises:
		SpeedProcessingError: If speed adjustment fails
	"""
	if speed == 1.0:
		LOGGER.info("Speed 1.0x (no adjustment needed)")
		return

	# Get cache
	cache = get_speed_cache()

	# Check which files exist (MP3 or WAV)
	vocal_files = list(output_dir.glob("vocals.*"))
	accompaniment_files = list(output_dir.glob("accompaniment.*"))

	if not vocal_files or not accompaniment_files:
		LOGGER.warning("Could not find stems to adjust speed")
		return

	vocal_file = vocal_files[0]
	accompaniment_file = accompaniment_files[0]

	try:
		# Check cache for vocal file
		cached_vocal = cache.get_cached_file(vocal_file, speed, "vocals")
		if cached_vocal:
			vocal_file.unlink()
			import shutil
			shutil.copy2(cached_vocal, vocal_file)
		else:
			# Adjust vocal speed
			vocal_output = output_dir / f"{vocal_file.stem}_adjusted{vocal_file.suffix}"
			_stretch_to_matching_format(vocal_file, vocal_output, speed)
			vocal_file.unlink()
			vocal_output.rename(vocal_file)
			# Cache result
			cache.cache_file(vocal_file, speed, "vocals", vocal_file, {})

		# Check cache for accompaniment file
		cached_accompaniment = cache.get_cached_file(accompaniment_file, speed, "accompaniment")
		if cached_accompaniment:
			accompaniment_file.unlink()
			import shutil
			shutil.copy2(cached_accompaniment, accompaniment_file)
		else:
			# Adjust accompaniment speed
			accompaniment_output = output_dir / f"{accompaniment_file.stem}_adjusted{accompaniment_file.suffix}"
			_stretch_to_matching_format(accompaniment_file, accompaniment_output, speed)
			accompaniment_file.unlink()
			accompaniment_output.rename(accompaniment_file)
			# Cache result
			cache.cache_file(accompaniment_file, speed, "accompaniment", accompaniment_file, {})

		LOGGER.info("Speed adjustment completed for task in %s (speed: %sx)", output_dir, speed)

	except Exception as e:
		raise SpeedProcessingError(f"Failed to adjust speed in {output_dir}: {str(e)}")


def _produce_speed_variant(output_dir: Path, speed: float, on_progress=None) -> dict[str, Path]:
	"""
	Produce speed-adjusted copies of the master stems without mutating them.

	Unlike _apply_speed_adjustment (used at upload time, which rewrites the
	stems in place), this reads from the canonical vocals.*/accompaniment.*
	files and writes the result into a dedicated subfolder, so the master
	stems stay at their original speed and repeated calls for different
	speeds never stack on top of each other.

	Args:
		output_dir: Directory containing the master vocal/accompaniment files
		speed: Speed factor (0.5-2.0, excluding 1.0)
		on_progress: Optional callback(fraction: float) for progress reporting

	Returns:
		Dict with "vocals" and "accompaniment" Paths to the adjusted files

	Raises:
		FileNotFoundError: If master stems are missing
		SpeedProcessingError: If speed adjustment fails
	"""
	cache = get_speed_cache()

	vocal_files = list(output_dir.glob("vocals.*"))
	accompaniment_files = list(output_dir.glob("accompaniment.*"))
	if not vocal_files or not accompaniment_files:
		raise FileNotFoundError(f"Master stems not found in {output_dir}")

	vocal_master = vocal_files[0]
	accompaniment_master = accompaniment_files[0]

	variant_dir = output_dir / f"speed_{speed}"
	variant_dir.mkdir(parents=True, exist_ok=True)

	result: dict[str, Path] = {}
	try:
		for label, master in (("vocals", vocal_master), ("accompaniment", accompaniment_master)):
			target = variant_dir / f"{label}{master.suffix}"

			cached = cache.get_cached_file(master, speed, label)
			if cached:
				if cached.resolve() != target.resolve():
					shutil.copy2(cached, target)
			else:
				_stretch_to_matching_format(master, target, speed)
				cache.cache_file(master, speed, label, target, {})

			result[label] = target
			if on_progress:
				on_progress(0.5 if label == "vocals" else 1.0)

		LOGGER.info("Speed variant %sx produced for %s", speed, output_dir)
		return result

	except Exception as e:
		raise SpeedProcessingError(f"Failed to produce {speed}x variant in {output_dir}: {str(e)}")


def _shift_to_matching_format(source: Path, target: Path, semitones: float) -> None:
	"""
	Pitch-shift `source` by `semitones`, writing to `target` in target's
	own format. Same MP3 workaround as _stretch_to_matching_format:
	soundfile can't write MP3, so shift into a temp WAV then re-encode.
	"""
	target_format = target.suffix.lstrip(".").lower()
	if target_format in ("wav", "flac", "ogg"):
		adjust_pitch(source, target, semitones)
		return

	temp_wav = target.parent / f"{target.stem}_pitch_tmp.wav"
	try:
		adjust_pitch(source, temp_wav, semitones)
		from .audio_converter import convert_audio

		convert_audio(temp_wav, target, target_format, bitrate=None)
	finally:
		temp_wav.unlink(missing_ok=True)


def _produce_pitch_variant(output_dir: Path, semitones: float, on_progress=None) -> dict[str, Path]:
	"""
	Produce a pitch-shifted copy of the ACCOMPANIMENT stem only (per the
	feature scope: key change applies to the "minus" track). The master
	stems are never mutated; the result goes into a dedicated subfolder.

	Args:
		output_dir: Directory containing the master accompaniment file
		semitones: Shift amount (-6 to +6, excluding 0)
		on_progress: Optional callback(fraction: float)

	Returns:
		Dict with an "accompaniment" Path to the shifted file

	Raises:
		FileNotFoundError: If the master accompaniment stem is missing
		PitchProcessingError: If pitch shifting fails
	"""
	cache = get_pitch_cache()

	accompaniment_files = list(output_dir.glob("accompaniment.*"))
	if not accompaniment_files:
		raise FileNotFoundError(f"Master accompaniment stem not found in {output_dir}")
	master = accompaniment_files[0]

	variant_dir = output_dir / f"pitch_{semitones}"
	variant_dir.mkdir(parents=True, exist_ok=True)
	target = variant_dir / f"accompaniment{master.suffix}"

	try:
		cached = cache.get_cached_file(master, semitones, "accompaniment")
		if cached:
			if cached.resolve() != target.resolve():
				shutil.copy2(cached, target)
		else:
			_shift_to_matching_format(master, target, semitones)
			cache.cache_file(master, semitones, "accompaniment", target, {})

		if on_progress:
			on_progress(1.0)

		LOGGER.info("Pitch variant %s semitones produced for %s", semitones, output_dir)
		return {"accompaniment": target}

	except Exception as e:
		raise PitchProcessingError(
			f"Failed to produce {semitones}-semitone variant in {output_dir}: {str(e)}"
		)


def _safe_db(value: float) -> float | None:
	"""Clamp -inf/+inf/NaN loudness readings to a JSON-safe finite value."""
	if value is None or math.isnan(value):
		return None
	if math.isinf(value):
		return -100.0 if value < 0 else 0.0
	return round(float(value), 2)


def _apply_normalization(output_dir: Path, method: str = "peak") -> dict[str, Any] | None:
	"""
	Apply volume normalization to separated stems.

	Normalizes both vocals and accompaniment either to -1dB peak level
	("peak", default) or to -14 LUFS ("lufs", the YouTube loudness target).

	Args:
		output_dir: Directory containing vocal and accompaniment files
		method: "peak" or "lufs"

	Returns:
		Dict with before/after loudness (dB or LUFS) for each stem, or None
		if stems were not found.

	Raises:
		NormalizationError: If normalization fails
	"""
	from pathlib import Path

	# Check which files exist (MP3 or WAV)
	vocal_files = list(output_dir.glob("vocals.*"))
	accompaniment_files = list(output_dir.glob("accompaniment.*"))

	if not vocal_files or not accompaniment_files:
		LOGGER.warning("Could not find stems to normalize")
		return None

	vocal_file = vocal_files[0]
	accompaniment_file = accompaniment_files[0]

	# Create temporary paths for normalized files
	vocal_normalized = output_dir / f"{vocal_file.stem}_norm{vocal_file.suffix}"
	accompaniment_normalized = output_dir / f"{accompaniment_file.stem}_norm{accompaniment_file.suffix}"

	before_key, after_key = (
		("before_lufs", "after_lufs") if method == "lufs" else ("before_peak_dbfs", "after_peak_dbfs")
	)

	try:
		# Normalize vocal track
		vocal_result = normalize_audio_file(
			vocal_file,
			vocal_normalized,
			method=method,
			target_peak_dbfs=-1.0,
			target_lufs=-14.0,
		)

		# Normalize accompaniment track
		accompaniment_result = normalize_audio_file(
			accompaniment_file,
			accompaniment_normalized,
			method=method,
			target_peak_dbfs=-1.0,
			target_lufs=-14.0,
		)

		# Replace original files with normalized versions
		vocal_file.unlink()
		accompaniment_file.unlink()
		vocal_normalized.rename(vocal_file)
		accompaniment_normalized.rename(accompaniment_file)

		LOGGER.info("Volume normalization completed for task in %s (method: %s)", output_dir, method)

		return {
			"method": method,
			"vocals": {
				"before_db": _safe_db(vocal_result[before_key]),
				"after_db": _safe_db(vocal_result[after_key]),
			},
			"accompaniment": {
				"before_db": _safe_db(accompaniment_result[before_key]),
				"after_db": _safe_db(accompaniment_result[after_key]),
			},
		}

	except Exception as e:
		# Clean up temporary files if normalization failed
		vocal_normalized.unlink(missing_ok=True)
		accompaniment_normalized.unlink(missing_ok=True)
		raise NormalizationError(f"Failed to normalize audio in {output_dir}: {str(e)}")


def _run_separation_pipeline(
	self,
	task_id: str,
	audio_path: Path,
	output_dir: Path,
	separation_intensity: float,
	normalize: bool,
	speed: float,
	normalization_method: str,
	progress_start: int = 10,
	progress_end: int = 95,
) -> dict[str, Any]:
	"""
	Demucs separation + normalization + speed adjustment, shared by both the
	direct-upload task and the YouTube task so the two never drift apart.

	Reports progress scaled into [progress_start, progress_end] (e.g. an
	upload uses the whole 10-95 range, while a YouTube job reserves 0-30
	for the download stage and gives this only 30-95).
	"""
	span = progress_end - progress_start

	def pct(fraction: float) -> int:
		return progress_start + int(span * fraction)

	def set_progress(fraction: float) -> None:
		self.update_state(
			state="PROCESSING",
			meta={"stage": "separating", "progress": pct(fraction), "task_id": task_id},
		)

	set_progress(0.0)
	_validate_audio_file(audio_path)

	output_dir.mkdir(parents=True, exist_ok=True)
	set_progress(0.1)

	separator = get_or_create_separator()
	set_progress(0.2)

	def report(fraction: float) -> None:
		set_progress(0.2 + 0.6 * fraction)

	_separate_stems(separator, audio_path, output_dir, separation_intensity=separation_intensity, on_progress=report)

	# Apply volume normalization if enabled
	normalization_result = None
	if normalize:
		set_progress(0.92)
		try:
			normalization_result = _apply_normalization(output_dir, method=normalization_method)
			LOGGER.info("Volume normalization applied to stems (method: %s)", normalization_method)
		except NormalizationError as e:
			LOGGER.warning("Volume normalization failed (continuing without it): %s", e)
			# Continue without normalization rather than failing the entire task

	# Apply speed adjustment if not 1.0x
	if speed != 1.0:
		set_progress(0.94)
		try:
			_apply_speed_adjustment(output_dir, speed)
			LOGGER.info("Speed adjustment applied to stems (speed: %sx)", speed)
		except (InvalidSpeedError, SpeedProcessingError) as e:
			LOGGER.warning("Speed adjustment failed (continuing without it): %s", e)
			# Continue without speed adjustment rather than failing the entire task

	# Verify output files (check for both WAV and MP3)
	has_vocals = (output_dir / "vocals.mp3").is_file() or (output_dir / "vocals.wav").is_file()
	has_accompaniment = (output_dir / "accompaniment.mp3").is_file() or (output_dir / "accompaniment.wav").is_file()
	if not (has_vocals and has_accompaniment):
		raise FileNotFoundError("Demucs did not produce both expected stems")
	set_progress(0.99)

	return {
		"task_id": task_id,
		"status": "SUCCESS",
		"stage": "separating",
		"progress": progress_end,
		"vocals_url": f"/api/download/{task_id}/vocals",
		"accompaniment_url": f"/api/download/{task_id}/accompaniment",
		"normalization": normalization_result,
	}


@celery_app.task(
	bind=True,
	base=CallbackTask,
	name="backend.tasks.process_audio_task",
	max_retries=2,
)
def process_audio_task(
	self,
	task_id: str,
	file_path: str,
	separation_intensity: float = 0.5,
	normalize: bool = True,
	speed: float = 1.0,
	normalization_method: str = "peak",
	trim_start_seconds: float | None = None,
	trim_end_seconds: float | None = None,
) -> dict[str, Any]:
	"""Separate one uploaded file into vocals and accompaniment WAV files.

	Args:
		separation_intensity: Vocal emphasis (0.0-1.0, default 0.5 for balanced)
		normalize: Apply volume normalization after separation (default: True)
		speed: Speed adjustment factor (0.5-2.0, default 1.0 for no change)
		normalization_method: "peak" (-1dBFS) or "lufs" (-14 LUFS, YouTube target)
		trim_start_seconds: Optional start time in seconds for audio trimming
		trim_end_seconds: Optional end time in seconds for audio trimming
	"""
	output_dir = OUTPUTS_DIR / task_id
	audio_path = Path(file_path).resolve()
	try:
		# Apply audio trimming if specified (saves processing time & resources)
		if trim_start_seconds is not None and trim_end_seconds is not None:
			self.update_state(state="PROCESSING", meta={"progress": 5, "stage": "trimming", "task_id": task_id})
			try:
				trimmed_path = output_dir / "trimmed_input.wav"
				output_dir.mkdir(parents=True, exist_ok=True)
				trim_result = trim_audio(audio_path, trimmed_path, trim_start_seconds, trim_end_seconds)
				LOGGER.info(
					"Audio trimmed: %.2f → %.2f seconds (%.1f%% reduction)",
					trim_result["original_duration"],
					trim_result["trimmed_duration"],
					100 * (1 - trim_result["trimmed_duration"] / trim_result["original_duration"]),
				)
				audio_path = trimmed_path  # Use trimmed audio for separation
				log_memory_usage("after_trimming")
			except InvalidTrimRangeError as e:
				raise ValueError(f"Invalid trim range: {str(e)}") from e
			except TrimError as e:
				LOGGER.warning("Audio trimming failed (continuing without trim): %s", e)
				# Continue without trimming if it fails

		result = _run_separation_pipeline(
			self, task_id, audio_path, output_dir,
			separation_intensity, normalize, speed, normalization_method,
			progress_start=10, progress_end=95,
		)

		log_memory_usage("after_separation")

		# Optimization: Delete upload immediately after successful processing (save 300 MB)
		audio_path.unlink(missing_ok=True)
		LOGGER.info("Optimization: Upload deleted immediately (freed ~300 MB)")
		log_memory_usage("after_upload_deletion")

		result["progress"] = 100
		self.update_state(state="SUCCESS", meta=result)

		# Optimization: Force garbage collection (save ~50-100 MB per 100 tasks)
		gc.collect()
		log_memory_usage("after_garbage_collection")
		LOGGER.info("Optimization: Garbage collection forced after task success")

		return result
	except Exception as exc:
		LOGGER.exception("Audio processing failed for task %s", task_id)
		if self.request.retries < self.max_retries:
			raise self.retry(exc=exc, countdown=5)
		raise
	finally:
		# Optimization: Force garbage collection even on error
		gc.collect()


@celery_app.task(
	bind=True,
	base=CallbackTask,
	name="backend.tasks.process_youtube_task",
	max_retries=1,
)
def process_youtube_task(
	self,
	task_id: str,
	url: str,
	separation_intensity: float = 0.5,
	normalize: bool = True,
	speed: float = 1.0,
	normalization_method: str = "peak",
) -> dict[str, Any]:
	"""Download audio from a YouTube URL, then run it through the same
	separation pipeline as a direct upload (Feature 7).

	Progress is reported in two stages: 0-30% while downloading, 30-95%
	while separating (see _run_separation_pipeline), matching the two-stage
	UI in the frontend.
	"""
	output_dir = OUTPUTS_DIR / task_id
	download_dir = UPLOADS_DIR / f"yt_{task_id}"
	downloaded_path: Path | None = None
	try:
		self.update_state(state="PROCESSING", meta={"stage": "downloading", "progress": 0, "task_id": task_id})

		# yt-dlp's progress hook fires from the download worker thread, which
		# has no Celery task context - so it can only write to a shared
		# holder. Only the main thread (polling below) is allowed to call
		# self.update_state, matching the pattern _separate_stems uses for
		# Demucs progress.
		progress_holder = {"fraction": 0.0}

		def dl_progress(fraction: float) -> None:
			progress_holder["fraction"] = fraction

		def _download_with_timeout() -> Path:
			with ThreadPoolExecutor(max_workers=1) as pool:
				future = pool.submit(
					download_audio, url, download_dir, YOUTUBE_AUDIO_BITRATE_KBPS, dl_progress
				)
				started = time.monotonic()
				while not future.done():
					if time.monotonic() - started > YOUTUBE_DOWNLOAD_TIMEOUT_SECONDS:
						raise TimeoutError(f"Download exceeded {YOUTUBE_DOWNLOAD_TIMEOUT_SECONDS}s")
					self.update_state(
						state="PROCESSING",
						meta={
							"stage": "downloading",
							"progress": int(30 * progress_holder["fraction"]),
							"task_id": task_id,
						},
					)
					time.sleep(1)
				return future.result()

		downloaded_path = _download_with_timeout()

		result = _run_separation_pipeline(
			self, task_id, downloaded_path, output_dir,
			separation_intensity, normalize, speed, normalization_method,
			progress_start=30, progress_end=95,
		)

		downloaded_path.unlink(missing_ok=True)
		shutil.rmtree(download_dir, ignore_errors=True)
		LOGGER.info("YouTube source audio deleted after successful separation")

		result["progress"] = 100
		self.update_state(state="SUCCESS", meta=result)

		gc.collect()
		return result

	except (InvalidURLError, VideoTooLongError, VideoUnavailableError, YouTubeExtractionError) as exc:
		# Not transient - retrying won't help a bad URL or a too-long video.
		LOGGER.warning("YouTube extraction failed for task %s: %s", task_id, exc)
		raise
	except TimeoutError as exc:
		LOGGER.warning("YouTube download timed out for task %s after %ss", task_id, YOUTUBE_DOWNLOAD_TIMEOUT_SECONDS)
		raise YouTubeExtractionError(
			f"Download timed out after {YOUTUBE_DOWNLOAD_TIMEOUT_SECONDS}s"
		) from exc
	except Exception as exc:
		LOGGER.exception("YouTube processing failed for task %s", task_id)
		if self.request.retries < self.max_retries:
			raise self.retry(exc=exc, countdown=5)
		raise
	finally:
		if downloaded_path is not None:
			downloaded_path.unlink(missing_ok=True)
		shutil.rmtree(download_dir, ignore_errors=True)
		gc.collect()


@celery_app.task(
	bind=True,
	base=CallbackTask,
	name="backend.tasks.apply_speed_task",
	max_retries=1,
)
def apply_speed_task(self, source_task_id: str, speed: float) -> dict[str, Any]:
	"""Produce a speed-adjusted copy of a completed task's stems.

	Reads the already-separated master stems for source_task_id and writes
	pitch-preserving time-stretched copies at the requested speed, without
	touching the master files (see _produce_speed_variant).
	"""
	output_dir = OUTPUTS_DIR / source_task_id
	try:
		self.update_state(state="PROCESSING", meta={"progress": 5})

		def report(fraction: float) -> None:
			self.update_state(state="PROCESSING", meta={"progress": 5 + int(90 * fraction)})

		_produce_speed_variant(output_dir, speed, on_progress=report)

		result = {
			"status": "SUCCESS",
			"progress": 100,
			"source_task_id": source_task_id,
			"speed": speed,
			"vocals_url": f"/api/download/{source_task_id}/vocals?speed={speed}",
			"accompaniment_url": f"/api/download/{source_task_id}/accompaniment?speed={speed}",
		}
		self.update_state(state="SUCCESS", meta=result)
		return result
	except Exception as exc:
		LOGGER.exception("Speed variant task failed for %s at %sx", source_task_id, speed)
		if self.request.retries < self.max_retries:
			raise self.retry(exc=exc, countdown=3)
		raise


@celery_app.task(
	bind=True,
	base=CallbackTask,
	name="backend.tasks.apply_pitch_task",
	max_retries=1,
)
def apply_pitch_task(self, source_task_id: str, semitones: float) -> dict[str, Any]:
	"""Produce a pitch-shifted copy of a completed task's ACCOMPANIMENT
	stem (the "minus" track), keeping tempo unchanged and without touching
	the master files (see _produce_pitch_variant).
	"""
	output_dir = OUTPUTS_DIR / source_task_id
	try:
		self.update_state(state="PROCESSING", meta={"progress": 5})

		def report(fraction: float) -> None:
			self.update_state(state="PROCESSING", meta={"progress": 5 + int(90 * fraction)})

		_produce_pitch_variant(output_dir, semitones, on_progress=report)

		result = {
			"status": "SUCCESS",
			"progress": 100,
			"source_task_id": source_task_id,
			"semitones": semitones,
			"accompaniment_url": f"/api/download/{source_task_id}/accompaniment?pitch={semitones}",
		}
		self.update_state(state="SUCCESS", meta=result)
		return result
	except Exception as exc:
		LOGGER.exception("Pitch variant task failed for %s at %s semitones", source_task_id, semitones)
		if self.request.retries < self.max_retries:
			raise self.retry(exc=exc, countdown=3)
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
