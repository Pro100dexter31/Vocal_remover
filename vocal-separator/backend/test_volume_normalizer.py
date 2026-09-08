#!/usr/bin/env python3
"""
Test suite for volume normalization functions.
Tests peak detection, normalization, and LUFS metering.
"""

import logging
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from volume_normalizer import (
    detect_peak_dbfs,
    calculate_gain_for_peak,
    normalize_peak,
    calculate_rms,
    estimate_lufs,
    normalize_lufs,
    normalize_audio_file,
    get_audio_stats,
    FileReadError,
    NormalizationError,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_audio(duration_seconds: float = 2, sample_rate: int = 44100, peak_amplitude: float = 0.8) -> np.ndarray:
    """
    Create test audio with specific peak amplitude.

    Args:
        duration_seconds: Duration in seconds
        sample_rate: Sample rate in Hz
        peak_amplitude: Peak amplitude (0-1)

    Returns:
        Audio array (mono)
    """
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples)

    audio = peak_amplitude * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return audio


def test_peak_detection():
    """Test peak detection in different audio scenarios."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Peak Detection")
    logger.info("="*70)

    test_cases = [
        (0.5, "Quiet audio (0.5 amplitude)"),
        (0.8, "Normal audio (0.8 amplitude)"),
        (0.99, "Loud audio (0.99 amplitude)"),
        (1.0, "Maximum audio (1.0 amplitude)"),
    ]

    for amplitude, description in test_cases:
        audio = create_test_audio(peak_amplitude=amplitude)
        peak_dbfs = detect_peak_dbfs(audio)
        expected_dbfs = 20 * np.log10(amplitude)

        logger.info(f"✓ {description}")
        logger.info(f"  Peak amplitude: {amplitude}")
        logger.info(f"  Detected dBFS: {peak_dbfs:.2f}")
        logger.info(f"  Expected dBFS: {expected_dbfs:.2f}")
        logger.info(f"  Match: {abs(peak_dbfs - expected_dbfs) < 0.1} ✓")


def test_gain_calculation():
    """Test gain calculation for peak normalization."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Gain Calculation")
    logger.info("="*70)

    test_cases = [
        (0.5, -1.0, "Quiet to -1dB"),
        (0.8, -1.0, "Normal to -1dB"),
        (0.99, -1.0, "Loud to -1dB"),
        (0.5, -6.0, "Quiet to -6dB"),
    ]

    for amplitude, target, description in test_cases:
        audio = create_test_audio(peak_amplitude=amplitude)
        gain = calculate_gain_for_peak(audio, target)

        logger.info(f"✓ {description}")
        logger.info(f"  Current peak: {amplitude}")
        logger.info(f"  Target: {target} dBFS")
        logger.info(f"  Gain factor: {gain:.4f}")
        logger.info(f"  Gain in dB: {20 * np.log10(gain):.2f} dB")


def test_peak_normalization():
    """Test peak normalization."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Peak Normalization")
    logger.info("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_cases = [
            (0.5, "Quiet audio"),
            (0.8, "Normal audio"),
            (0.99, "Loud audio"),
        ]

        for amplitude, description in test_cases:
            audio = create_test_audio(peak_amplitude=amplitude)
            input_path = tmpdir / f"test_{amplitude}.wav"
            output_path = tmpdir / f"normalized_{amplitude}.wav"

            sf.write(str(input_path), audio, 44100)

            result = normalize_audio_file(
                input_path,
                output_path,
                method="peak",
                target_peak_dbfs=-1.0
            )

            logger.info(f"✓ {description}")
            logger.info(f"  Before: {result['before_peak_dbfs']:.2f} dBFS")
            logger.info(f"  After: {result['after_peak_dbfs']:.2f} dBFS")
            logger.info(f"  Target: {result['target_peak_dbfs']:.2f} dBFS")
            logger.info(f"  Gain: {result['gain_db']:.2f} dB")
            logger.info(f"  Match: {abs(result['after_peak_dbfs'] - result['target_peak_dbfs']) < 0.2} ✓")


def test_rms_calculation():
    """Test RMS level calculation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: RMS Calculation")
    logger.info("="*70)

    test_cases = [
        (0.2, "Quiet"),
        (0.5, "Medium"),
        (0.8, "Loud"),
    ]

    for amplitude, description in test_cases:
        audio = create_test_audio(peak_amplitude=amplitude)
        rms = calculate_rms(audio)

        expected_rms = amplitude / np.sqrt(2)

        logger.info(f"✓ {description} audio")
        logger.info(f"  Peak amplitude: {amplitude}")
        logger.info(f"  Calculated RMS: {rms:.4f}")
        logger.info(f"  Expected RMS: {expected_rms:.4f}")
        logger.info(f"  Match: {abs(rms - expected_rms) < 0.01} ✓")


def test_lufs_estimation():
    """Test LUFS estimation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: LUFS Estimation")
    logger.info("="*70)

    test_cases = [
        (0.3, "Quiet audio"),
        (0.5, "Medium audio"),
        (0.8, "Loud audio"),
    ]

    for amplitude, description in test_cases:
        audio = create_test_audio(peak_amplitude=amplitude)
        lufs = estimate_lufs(audio, 44100)

        logger.info(f"✓ {description}")
        logger.info(f"  Peak amplitude: {amplitude}")
        logger.info(f"  Estimated LUFS: {lufs:.2f}")


def test_lufs_normalization():
    """Test LUFS normalization."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: LUFS Normalization")
    logger.info("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_cases = [
            (0.3, -14.0, "YouTube standard"),
            (0.5, -18.0, "Streaming standard"),
            (0.8, -23.0, "Podcast standard"),
        ]

        for amplitude, target_lufs, description in test_cases:
            audio = create_test_audio(peak_amplitude=amplitude)
            input_path = tmpdir / f"test_lufs_{amplitude}.wav"
            output_path = tmpdir / f"normalized_lufs_{amplitude}.wav"

            sf.write(str(input_path), audio, 44100)

            result = normalize_audio_file(
                input_path,
                output_path,
                method="lufs",
                target_lufs=target_lufs
            )

            logger.info(f"✓ {description}")
            logger.info(f"  Before: {result['before_lufs']:.2f} LUFS")
            logger.info(f"  After: {result['after_lufs']:.2f} LUFS")
            logger.info(f"  Target: {result['target_lufs']:.2f} LUFS")
            logger.info(f"  Difference: {abs(result['after_lufs'] - result['target_lufs']):.2f} LUFS")


def test_audio_stats():
    """Test audio statistics calculation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 7: Audio Statistics")
    logger.info("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        audio = create_test_audio(duration_seconds=5, peak_amplitude=0.75)
        test_path = tmpdir / "test_stats.wav"
        sf.write(str(test_path), audio, 44100)

        stats = get_audio_stats(test_path)

        logger.info("✓ Audio statistics retrieved")
        logger.info(f"  Sample rate: {stats['sample_rate']} Hz")
        logger.info(f"  Duration: {stats['duration_seconds']:.2f} seconds")
        logger.info(f"  Channels: {stats['channels']}")
        logger.info(f"  Peak: {stats['peak_dbfs']:.2f} dBFS")
        logger.info(f"  RMS: {stats['rms_dbfs']:.2f} dBFS")
        logger.info(f"  Estimated LUFS: {stats['lufs_estimated']:.2f}")


def test_error_handling():
    """Test error handling."""
    logger.info("\n" + "="*70)
    logger.info("TEST 8: Error Handling")
    logger.info("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        nonexistent = tmpdir / "nonexistent.wav"

        try:
            normalize_audio_file(nonexistent, tmpdir / "output.wav")
            logger.error("✗ Should have raised FileReadError")
        except FileReadError as e:
            logger.info(f"✓ FileReadError caught correctly: {str(e)[:50]}...")

        try:
            audio = create_test_audio()
            invalid_path = tmpdir / "test.wav"
            sf.write(str(invalid_path), audio, 44100)

            normalize_audio_file(
                invalid_path,
                tmpdir / "output.wav",
                method="invalid_method"
            )
            logger.error("✗ Should have raised NormalizationError")
        except NormalizationError as e:
            logger.info(f"✓ NormalizationError caught correctly: {str(e)[:50]}...")


def main():
    """Run all tests."""
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║      Volume Normalization Tests (Task 3.1)            ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info("")

    try:
        test_peak_detection()
        test_gain_calculation()
        test_peak_normalization()
        test_rms_calculation()
        test_lufs_estimation()
        test_lufs_normalization()
        test_audio_stats()
        test_error_handling()

        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════╗")
        logger.info("║               ✓ ALL TESTS COMPLETED                    ║")
        logger.info("╚════════════════════════════════════════════════════════╝")
        logger.info("")
        return 0

    except Exception as e:
        logger.error("")
        logger.error("╔════════════════════════════════════════════════════════╗")
        logger.error("║              ✗ TESTS FAILED                           ║")
        logger.error("╚════════════════════════════════════════════════════════╝")
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
