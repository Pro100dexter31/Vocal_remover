"""
Volume normalization module for audio processing.
Implements peak-based and LUFS-based loudness normalization.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Tuple

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

LOGGER = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


class FileReadError(NormalizationError):
    """Raised when audio file cannot be read."""
    pass


class NormalizationCalculationError(NormalizationError):
    """Raised when normalization calculation fails."""
    pass


def _read_audio(file_path: str | Path) -> Tuple[np.ndarray, int]:
    """
    Read audio file and return audio data and sample rate.

    Args:
        file_path: Path to audio file

    Returns:
        Tuple of (audio_data, sample_rate)

    Raises:
        FileReadError: If file cannot be read
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileReadError(f"Audio file not found: {file_path}")

    try:
        if LIBROSA_AVAILABLE:
            audio, sr = librosa.load(str(file_path), sr=None, mono=False)
            return audio, sr
        elif SOUNDFILE_AVAILABLE:
            audio, sr = sf.read(str(file_path))
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]
            else:
                audio = audio.T
            return audio.astype(np.float32), sr
        else:
            raise FileReadError("No audio reading library available (librosa or soundfile)")
    except Exception as e:
        raise FileReadError(f"Failed to read audio file '{file_path}': {str(e)}")


def _write_audio(audio: np.ndarray, sample_rate: int, output_path: str | Path) -> None:
    """
    Write audio data to file.

    Args:
        audio: Audio data (mono or stereo)
        sample_rate: Sample rate in Hz
        output_path: Path to output file

    Raises:
        NormalizationError: If file cannot be written
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if audio.ndim > 1:
            audio = audio.T
        sf.write(str(output_path), audio, sample_rate)
    except Exception as e:
        raise NormalizationError(f"Failed to write audio file '{output_path}': {str(e)}")


def detect_peak_dbfs(audio: np.ndarray) -> float:
    """
    Detect peak amplitude in dBFS (decibels relative to full scale).

    Args:
        audio: Audio data (mono or stereo)

    Returns:
        Peak amplitude in dBFS
    """
    if audio.ndim > 1:
        peak_amplitude = np.max(np.abs(audio))
    else:
        peak_amplitude = np.max(np.abs(audio))

    if peak_amplitude <= 0:
        return -np.inf

    peak_dbfs = 20 * np.log10(peak_amplitude)
    return peak_dbfs


def calculate_gain_for_peak(audio: np.ndarray, target_peak_dbfs: float = -1.0) -> float:
    """
    Calculate gain factor needed to reach target peak level.

    Args:
        audio: Audio data
        target_peak_dbfs: Target peak level in dBFS (default: -1 dB)

    Returns:
        Gain factor (linear scale)
    """
    current_peak = detect_peak_dbfs(audio)

    if current_peak == -np.inf or current_peak >= target_peak_dbfs:
        return 1.0

    gain_db = target_peak_dbfs - current_peak
    gain_linear = 10 ** (gain_db / 20)

    return gain_linear


def normalize_peak(
    audio: np.ndarray,
    target_peak_dbfs: float = -1.0,
) -> Tuple[np.ndarray, float]:
    """
    Normalize audio to target peak level.

    Args:
        audio: Audio data (mono or stereo)
        target_peak_dbfs: Target peak level in dBFS (default: -1 dB)

    Returns:
        Tuple of (normalized_audio, gain_applied)
    """
    gain = calculate_gain_for_peak(audio, target_peak_dbfs)

    if gain <= 1.0:
        normalized = audio * gain
    else:
        normalized = np.clip(audio * gain, -1.0, 1.0)

    return normalized.astype(np.float32), gain


def calculate_rms(audio: np.ndarray) -> float:
    """
    Calculate RMS (Root Mean Square) level.

    Args:
        audio: Audio data

    Returns:
        RMS level (linear scale, 0-1)
    """
    if audio.size == 0:
        return 0.0

    if audio.ndim > 1:
        rms = np.sqrt(np.mean(audio ** 2))
    else:
        rms = np.sqrt(np.mean(audio ** 2))

    return float(rms)


def estimate_lufs(audio: np.ndarray, sample_rate: int) -> float:
    """
    Estimate LUFS (Loudness Units relative to Full Scale).

    Simple estimation based on RMS. For precise LUFS measurement,
    use dedicated loudness metering libraries.

    Args:
        audio: Audio data
        sample_rate: Sample rate in Hz

    Returns:
        Estimated LUFS value
    """
    rms = calculate_rms(audio)

    if rms <= 0:
        return -np.inf

    lufs_estimated = -0.691 + 10 * np.log10(rms + 1e-10)

    return lufs_estimated


def normalize_lufs(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -14.0,
) -> Tuple[np.ndarray, float, float]:
    """
    Normalize audio to target LUFS level.

    Note: This is a simplified LUFS normalization. For production use,
    consider using dedicated loudness metering libraries (pyloudnorm, etc).

    Args:
        audio: Audio data
        sample_rate: Sample rate in Hz
        target_lufs: Target LUFS level (default: -14.0 LUFS for YouTube)

    Returns:
        Tuple of (normalized_audio, current_lufs, target_lufs)
    """
    current_lufs = estimate_lufs(audio, sample_rate)

    if current_lufs == -np.inf or current_lufs >= target_lufs:
        return audio.astype(np.float32), current_lufs, target_lufs

    gain_db = target_lufs - current_lufs
    gain_linear = 10 ** (gain_db / 20)

    normalized = np.clip(audio * gain_linear, -1.0, 1.0)

    return normalized.astype(np.float32), current_lufs, target_lufs


def normalize_audio_file(
    input_path: str | Path,
    output_path: str | Path,
    method: str = "peak",
    target_peak_dbfs: float = -1.0,
    target_lufs: float = -14.0,
) -> dict:
    """
    Normalize audio file.

    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file
        method: Normalization method ("peak" or "lufs")
        target_peak_dbfs: Target peak for peak normalization
        target_lufs: Target LUFS for LUFS normalization

    Returns:
        Dictionary with normalization results

    Raises:
        FileReadError: If input file cannot be read
        NormalizationCalculationError: If normalization fails
    """
    try:
        audio, sample_rate = _read_audio(input_path)

        if method == "peak":
            normalized_audio, gain = normalize_peak(audio, target_peak_dbfs)
            before_peak = detect_peak_dbfs(audio)
            after_peak = detect_peak_dbfs(normalized_audio)

            _write_audio(normalized_audio, sample_rate, output_path)

            return {
                "method": "peak",
                "sample_rate": sample_rate,
                "gain_applied": float(gain),
                "gain_db": 20 * np.log10(gain),
                "before_peak_dbfs": float(before_peak),
                "after_peak_dbfs": float(after_peak),
                "target_peak_dbfs": target_peak_dbfs,
                "output_file": str(output_path),
            }

        elif method == "lufs":
            normalized_audio, current_lufs, _ = normalize_lufs(
                audio, sample_rate, target_lufs
            )

            _write_audio(normalized_audio, sample_rate, output_path)

            gain = np.max(np.abs(normalized_audio)) / (np.max(np.abs(audio)) + 1e-10)

            return {
                "method": "lufs",
                "sample_rate": sample_rate,
                "before_lufs": float(current_lufs),
                "after_lufs": float(estimate_lufs(normalized_audio, sample_rate)),
                "target_lufs": target_lufs,
                "gain_applied": float(gain),
                "output_file": str(output_path),
            }

        else:
            raise NormalizationCalculationError(
                f"Unknown normalization method: {method}. Use 'peak' or 'lufs'."
            )

    except (FileReadError, NormalizationError):
        raise
    except Exception as e:
        raise NormalizationCalculationError(
            f"Normalization failed for '{input_path}': {str(e)}"
        )


def get_audio_stats(file_path: str | Path) -> dict:
    """
    Get audio statistics without normalization.

    Args:
        file_path: Path to audio file

    Returns:
        Dictionary with audio statistics
    """
    try:
        audio, sample_rate = _read_audio(file_path)

        peak_dbfs = detect_peak_dbfs(audio)
        rms = calculate_rms(audio)
        rms_dbfs = 20 * np.log10(rms + 1e-10) if rms > 0 else -np.inf
        lufs_estimated = estimate_lufs(audio, sample_rate)

        return {
            "sample_rate": sample_rate,
            "duration_seconds": audio.shape[-1] / sample_rate if audio.ndim > 1 else len(audio) / sample_rate,
            "channels": audio.shape[0] if audio.ndim > 1 else 1,
            "peak_dbfs": float(peak_dbfs),
            "rms_dbfs": float(rms_dbfs),
            "rms_linear": float(rms),
            "lufs_estimated": float(lufs_estimated),
        }

    except FileReadError:
        raise
    except Exception as e:
        raise NormalizationError(f"Failed to get audio stats: {str(e)}")
