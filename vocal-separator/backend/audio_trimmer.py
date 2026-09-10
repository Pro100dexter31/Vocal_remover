"""Audio trimming/cutting functionality for extracting specific time ranges."""

import logging
from pathlib import Path

import librosa
import soundfile as sf

LOGGER = logging.getLogger(__name__)


class TrimError(Exception):
	"""Base exception for trimming errors."""
	pass


class InvalidTrimRangeError(TrimError):
	"""Raised when trim range is invalid."""
	pass


class TrimProcessingError(TrimError):
	"""Raised when audio trimming fails."""
	pass


def validate_trim_range(trim_start_seconds: float, trim_end_seconds: float, audio_duration: float) -> None:
	"""Validate trim start and end times.

	Args:
		trim_start_seconds: Start time in seconds (>= 0)
		trim_end_seconds: End time in seconds
		audio_duration: Total audio duration in seconds

	Raises:
		InvalidTrimRangeError: If range is invalid
	"""
	if trim_start_seconds < 0:
		raise InvalidTrimRangeError(f"trim_start must be >= 0, got {trim_start_seconds}")

	if trim_end_seconds <= trim_start_seconds:
		raise InvalidTrimRangeError(
			f"trim_end ({trim_end_seconds}s) must be > trim_start ({trim_start_seconds}s)"
		)

	if trim_start_seconds > audio_duration:
		raise InvalidTrimRangeError(
			f"trim_start ({trim_start_seconds}s) exceeds audio duration ({audio_duration}s)"
		)

	if trim_end_seconds > audio_duration:
		raise InvalidTrimRangeError(
			f"trim_end ({trim_end_seconds}s) exceeds audio duration ({audio_duration}s)"
		)


def trim_audio(
	input_path: Path,
	output_path: Path,
	trim_start_seconds: float,
	trim_end_seconds: float,
	sample_rate: int | None = None,
) -> dict[str, any]:
	"""Extract a specific time range from an audio file.

	Args:
		input_path: Path to input audio file
		output_path: Path to write trimmed audio
		trim_start_seconds: Start time in seconds
		trim_end_seconds: End time in seconds
		sample_rate: Optional target sample rate (default: detect from file)

	Returns:
		Dictionary with metadata:
		- original_duration: Duration before trimming (seconds)
		- trimmed_duration: Duration after trimming (seconds)
		- trim_start: Start time used (seconds)
		- trim_end: End time used (seconds)
		- saved_path: Path to output file

	Raises:
		InvalidTrimRangeError: If trim range is invalid
		TrimProcessingError: If trimming fails
	"""
	try:
		LOGGER.info("Loading audio: %s", input_path)
		waveform, sr = librosa.load(str(input_path), sr=sample_rate, mono=False)

		original_duration = librosa.get_duration(y=waveform, sr=sr)
		LOGGER.info("Audio duration: %.2f seconds", original_duration)

		# Validate trim range
		validate_trim_range(trim_start_seconds, trim_end_seconds, original_duration)

		# Convert time to samples
		start_sample = int(trim_start_seconds * sr)
		end_sample = int(trim_end_seconds * sr)

		# Extract trimmed audio
		if len(waveform.shape) > 1:  # Stereo or multi-channel
			trimmed = waveform[:, start_sample:end_sample]
		else:  # Mono
			trimmed = waveform[start_sample:end_sample]

		trimmed_duration = librosa.get_duration(y=trimmed, sr=sr)

		# Save trimmed audio
		LOGGER.info("Saving trimmed audio: %s (duration: %.2f seconds)", output_path, trimmed_duration)
		sf.write(str(output_path), trimmed.T if len(trimmed.shape) > 1 else trimmed, sr)

		LOGGER.info("Trim complete: %.2f → %.2f seconds", original_duration, trimmed_duration)

		return {
			"original_duration": float(original_duration),
			"trimmed_duration": float(trimmed_duration),
			"trim_start": float(trim_start_seconds),
			"trim_end": float(trim_end_seconds),
			"saved_path": str(output_path),
			"sample_rate": sr,
		}

	except InvalidTrimRangeError:
		raise
	except Exception as e:
		LOGGER.exception("Audio trimming failed: %s", e)
		raise TrimProcessingError(f"Failed to trim audio: {str(e)}") from e


def get_audio_duration(audio_path: Path) -> float:
	"""Get duration of audio file in seconds.

	Args:
		audio_path: Path to audio file

	Returns:
		Duration in seconds

	Raises:
		TrimProcessingError: If duration cannot be determined
	"""
	try:
		duration = librosa.get_duration(filename=str(audio_path))
		return float(duration)
	except Exception as e:
		raise TrimProcessingError(f"Could not determine audio duration: {str(e)}") from e
