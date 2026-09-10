"""Musical key (pitch) shifting, independent of tempo.

Complements speed_adjuster.py: that module changes tempo while preserving
pitch (time-stretch); this one changes pitch while preserving tempo
(librosa's phase-vocoder-based pitch_shift). The two are independent
transforms and are not composed together in this app - each produces its
own separate output variant.
"""

import logging
import shutil
from pathlib import Path

import librosa
import soundfile as sf

LOGGER = logging.getLogger(__name__)


class PitchAdjustmentError(Exception):
	"""Raised when pitch adjustment fails."""


class InvalidSemitonesError(PitchAdjustmentError):
	"""Raised when the requested shift is outside the supported range."""


class FileReadError(PitchAdjustmentError):
	"""Raised when the audio file cannot be read."""


class PitchProcessingError(PitchAdjustmentError):
	"""Raised when the pitch-shift itself fails."""


# Half an octave in each direction - beyond this, phase-vocoder pitch
# shifting starts sounding artificial/robotic on most material.
MIN_SEMITONES = -6
MAX_SEMITONES = 6

# Short-clip preview length: long enough to judge the new key, short
# enough to process in ~1-2s for a responsive "live" feel.
PREVIEW_DURATION_SECONDS = 8.0

# Previews trade fidelity for speed: half sample rate + fast resampler.
# Full-length renders keep the native rate and the high-quality path.
PREVIEW_SAMPLE_RATE = 22050


def validate_semitones(semitones: float) -> None:
	"""
	Validate a requested pitch shift.

	Args:
		semitones: Shift amount in semitones (-6 to +6)

	Raises:
		InvalidSemitonesError: If out of the supported range
	"""
	if not MIN_SEMITONES <= semitones <= MAX_SEMITONES:
		raise InvalidSemitonesError(
			f"Semitones must be between {MIN_SEMITONES} and {MAX_SEMITONES} (got {semitones})"
		)


def get_semitones_label(semitones: float) -> str:
	"""Human-readable label, e.g. '+2 semitones' or '-3 semitones'."""
	validate_semitones(semitones)
	sign = "+" if semitones > 0 else ""
	return f"{sign}{semitones:g} semitones"


def adjust_pitch(
	audio_path: Path,
	output_path: Path,
	semitones: float,
	max_duration_seconds: float | None = None,
) -> dict[str, str | float]:
	"""
	Shift the musical key of an audio file, keeping tempo unchanged.

	Args:
		audio_path: Path to input audio file
		output_path: Path to save the pitch-shifted audio
		semitones: Shift amount (-6 to +6); 0 copies the file unchanged
		max_duration_seconds: If set, only load/process this many seconds
			from the start - used for fast short-clip previews instead of
			processing the whole track

	Returns:
		Dict with processing info

	Raises:
		InvalidSemitonesError: If semitones is out of range
		FileReadError: If the audio file cannot be read
		PitchProcessingError: If processing fails
	"""
	validate_semitones(semitones)

	if semitones == 0:
		LOGGER.info("Semitones=0 (no change), copying file as-is")
		shutil.copy2(audio_path, output_path)
		return {
			"semitones": semitones,
			"status": "skipped",
			"reason": "0 semitones (no adjustment needed)",
		}

	is_preview = max_duration_seconds is not None
	try:
		LOGGER.info("Loading audio: %s (max_duration=%s, preview=%s)", audio_path, max_duration_seconds, is_preview)
		y, sr = librosa.load(
			audio_path,
			sr=PREVIEW_SAMPLE_RATE if is_preview else None,
			duration=max_duration_seconds,
			res_type="soxr_lq" if is_preview else "soxr_hq",
		)

		duration = librosa.get_duration(y=y, sr=sr)
		LOGGER.info("Audio loaded: %.2f seconds at %d Hz", duration, sr)

		LOGGER.info("Applying pitch shift: %s semitones", semitones)
		y_shifted = librosa.effects.pitch_shift(
			y, sr=sr, n_steps=semitones,
			res_type="soxr_lq" if is_preview else "soxr_hq",
		)

		LOGGER.info("Saving pitch-shifted audio: %s", output_path)
		sf.write(output_path, y_shifted, sr, subtype="PCM_16")

		return {
			"semitones": semitones,
			"status": "success",
			"duration": duration,
			"sample_rate": sr,
			"tempo_preserved": True,
		}

	except FileNotFoundError as e:
		LOGGER.error("Audio file not found: %s", audio_path)
		raise FileReadError(f"Audio file not found: {audio_path}") from e
	except PitchAdjustmentError:
		raise
	except Exception as e:
		LOGGER.exception("Pitch adjustment failed: %s", e)
		raise PitchProcessingError(f"Pitch adjustment failed: {str(e)}") from e
