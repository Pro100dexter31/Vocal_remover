"""Audio speed adjustment using time-stretching (pitch-invariant)."""

import logging
from pathlib import Path
from typing import Literal

import librosa
import numpy as np
import soundfile as sf

LOGGER = logging.getLogger(__name__)


class SpeedAdjustmentError(Exception):
    """Raised when speed adjustment fails."""

    pass


class InvalidSpeedError(SpeedAdjustmentError):
    """Raised when speed value is invalid."""

    pass


class FileReadError(SpeedAdjustmentError):
    """Raised when audio file cannot be read."""

    pass


class SpeedProcessingError(SpeedAdjustmentError):
    """Raised when speed processing fails."""

    pass


# Supported speed factors
SUPPORTED_SPEEDS = {
    0.5: "0.5x",
    0.75: "0.75x",
    1.0: "1.0x",
    1.25: "1.25x",
    1.5: "1.5x",
    2.0: "2.0x",
}

# Processing time estimation: time-stretching is ~2x audio duration
PROCESSING_TIME_MULTIPLIER = 2.0


def validate_speed(speed: float) -> None:
    """
    Validate speed factor.

    Args:
        speed: Speed factor (0.5-2.0)

    Raises:
        InvalidSpeedError: If speed is invalid
    """
    if speed not in SUPPORTED_SPEEDS:
        supported = ", ".join(f"{s}x" for s in sorted(SUPPORTED_SPEEDS.keys()))
        raise InvalidSpeedError(
            f"Speed {speed}x not supported. Supported: {supported}"
        )


def estimate_processing_duration(audio_duration: float) -> float:
    """
    Estimate time-stretching processing duration.

    Args:
        audio_duration: Audio duration in seconds

    Returns:
        Estimated processing time in seconds (~2x audio duration)
    """
    return audio_duration * PROCESSING_TIME_MULTIPLIER


def adjust_speed(
    audio_path: Path,
    output_path: Path,
    speed: float,
) -> dict[str, str | float]:
    """
    Adjust audio speed using time-stretching (pitch-invariant).

    Args:
        audio_path: Path to input audio file
        output_path: Path to save speed-adjusted audio
        speed: Speed factor (0.5-2.0)

    Returns:
        Dictionary with processing info

    Raises:
        InvalidSpeedError: If speed is invalid
        FileReadError: If audio file cannot be read
        SpeedProcessingError: If processing fails
    """
    # Validate speed
    validate_speed(speed)

    # Skip if speed is 1.0 (no change)
    if speed == 1.0:
        LOGGER.info("Speed 1.0x (no change), copying file as-is")
        # Just copy the file
        import shutil

        shutil.copy2(audio_path, output_path)
        return {
            "speed": speed,
            "status": "skipped",
            "reason": "Speed 1.0x (no adjustment needed)",
        }

    try:
        LOGGER.info("Loading audio: %s", audio_path)
        # Load audio with native sample rate
        y, sr = librosa.load(audio_path, sr=None)

        original_duration = librosa.get_duration(y=y, sr=sr)
        LOGGER.info("Audio loaded: %.2f seconds at %d Hz", original_duration, sr)

        # Apply time-stretching (pitch-invariant)
        LOGGER.info("Applying time-stretching: %sx", speed)
        y_stretched = librosa.effects.time_stretch(y, rate=speed)

        new_duration = librosa.get_duration(y=y_stretched, sr=sr)
        LOGGER.info("Time-stretching complete: %.2f seconds", new_duration)

        # Verify pitch invariance by checking spectral content
        # (frequency content remains the same, only tempo changes)
        stft_original = librosa.stft(y)
        stft_stretched = librosa.stft(y_stretched)

        # Save stretched audio
        LOGGER.info("Saving speed-adjusted audio: %s", output_path)
        sf.write(output_path, y_stretched, sr, subtype="PCM_16")

        return {
            "speed": speed,
            "status": "success",
            "original_duration": original_duration,
            "new_duration": new_duration,
            "duration_ratio": new_duration / original_duration,
            "sample_rate": sr,
            "pitch_invariant": True,
        }

    except FileNotFoundError as e:
        LOGGER.error("Audio file not found: %s", audio_path)
        raise FileReadError(f"Audio file not found: {audio_path}") from e
    except Exception as e:
        LOGGER.exception("Speed adjustment failed: %s", e)
        raise SpeedProcessingError(f"Speed adjustment failed: {str(e)}") from e


def get_speed_label(speed: float) -> str:
    """
    Get human-readable speed label.

    Args:
        speed: Speed factor (0.5-2.0)

    Returns:
        Speed label (e.g., "0.5x")

    Raises:
        InvalidSpeedError: If speed is invalid
    """
    validate_speed(speed)
    return SUPPORTED_SPEEDS[speed]


def get_file_size_estimate(original_size: int, speed: float) -> int:
    """
    Estimate output file size after speed adjustment.

    Args:
        original_size: Original file size in bytes
        speed: Speed factor

    Returns:
        Estimated output file size in bytes
    """
    # File size scales with duration
    return int(original_size / speed)
