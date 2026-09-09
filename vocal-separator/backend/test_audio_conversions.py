#!/usr/bin/env python3
"""
Test script for audio format conversions.
Tests WAV → MP3, FLAC, and OGG conversions with various bitrates.
"""

import logging
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the audio converter module
from audio_converter import (
    convert_audio,
    get_supported_formats,
    estimate_file_size,
    InvalidFormatError,
    InvalidBitrateError,
    AudioConversionError,
)


def create_test_wav(duration_seconds: float = 5, sample_rate: int = 44100) -> Path:
    """
    Create a test WAV file with audio data.

    Args:
        duration_seconds: Duration of test audio
        sample_rate: Sample rate in Hz

    Returns:
        Path to created WAV file
    """
    logger.info("Creating test WAV file (%d seconds at %d Hz)...", duration_seconds, sample_rate)

    # Create test audio (simple sine wave at 440 Hz)
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples)

    # Generate multiple sine waves for more realistic audio
    audio = (
        0.3 * np.sin(2 * np.pi * 440 * t) +   # A4
        0.2 * np.sin(2 * np.pi * 880 * t) +   # A5
        0.1 * np.sin(2 * np.pi * 220 * t)     # A3
    )
    audio = audio.astype(np.float32)

    # Write to temporary file
    temp_file = Path(tempfile.gettempdir()) / "test_audio.wav"
    sf.write(str(temp_file), audio, sample_rate)

    file_size_mb = temp_file.stat().st_size / (1024 * 1024)
    logger.info("✓ Test WAV created: %s (%.2f MB)", temp_file.name, file_size_mb)

    return temp_file


def test_format_validation():
    """Test that format validation works correctly."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Format Validation")
    logger.info("="*70)

    test_cases = [
        ("mp3", True),
        ("MP3", True),
        ("flac", True),
        ("ogg", True),
        ("wav", True),
        ("invalid", False),
        ("aac", False),
    ]

    for fmt, should_pass in test_cases:
        try:
            from audio_converter import _validate_format
            result = _validate_format(fmt)
            if should_pass:
                logger.info("✓ Format '%s' -> '%s'", fmt, result)
            else:
                logger.error("✗ Format '%s' should have failed but passed", fmt)
        except InvalidFormatError as e:
            if not should_pass:
                logger.info("✓ Format '%s' correctly rejected: %s", fmt, str(e)[:50])
            else:
                logger.error("✗ Format '%s' should have passed but failed", fmt)


def test_bitrate_validation():
    """Test that bitrate validation works correctly."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Bitrate Validation")
    logger.info("="*70)

    test_cases = [
        ("mp3", "128k", True),
        ("mp3", "192k", True),
        ("mp3", "320k", True),
        ("mp3", "256k", False),  # Invalid for MP3
        ("ogg", "128k", True),
        ("ogg", "192k", True),
        ("ogg", "320k", False),  # Invalid for OGG
        ("flac", None, True),    # Lossless, no bitrate
        ("flac", "192k", True),  # Bitrate ignored for lossless
    ]

    for fmt, bitrate, should_pass in test_cases:
        try:
            from audio_converter import _validate_bitrate, _validate_format
            fmt_validated = _validate_format(fmt)
            result = _validate_bitrate(fmt_validated, bitrate)
            if should_pass:
                logger.info("✓ Format '%s' with bitrate '%s' -> '%s'", fmt, bitrate, result)
            else:
                logger.error("✗ Should have failed: %s with bitrate %s", fmt, bitrate)
        except InvalidBitrateError as e:
            if not should_pass:
                logger.info("✓ Correctly rejected: %s %s", fmt, bitrate)
            else:
                logger.error("✗ Should have passed: %s %s", fmt, bitrate)


def test_conversions(wav_file: Path):
    """Test audio conversions for all formats."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Audio Format Conversions")
    logger.info("="*70)

    conversions = [
        ("mp3", "128k", "MP3 (128 kbps - Low Quality)"),
        ("mp3", "192k", "MP3 (192 kbps - Standard)"),
        ("mp3", "320k", "MP3 (320 kbps - High Quality)"),
        ("flac", None, "FLAC (Lossless)"),
        ("ogg", "128k", "OGG (128 kbps - Low Quality)"),
        ("ogg", "192k", "OGG (192 kbps - Standard)"),
        ("wav", None, "WAV (Lossless)"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        for fmt, bitrate, description in conversions:
            try:
                # Create output path
                output_file = tmpdir / f"test_audio.{fmt}"

                logger.info("\nConverting to: %s", description)

                # Perform conversion
                result = convert_audio(
                    wav_file,
                    output_file,
                    fmt,
                    bitrate=bitrate
                )

                # Check results
                if result.exists():
                    file_size = result.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    input_size_mb = wav_file.stat().st_size / (1024 * 1024)
                    compression = (1 - file_size / wav_file.stat().st_size) * 100

                    logger.info("✓ Conversion successful!")
                    logger.info("  Output: %s", result.name)
                    logger.info("  Size: %.2f MB (%.1f%% compression)", file_size_mb, compression)
                    logger.info("  Size ratio: %.2f%%", (file_size / wav_file.stat().st_size) * 100)
                else:
                    logger.error("✗ Output file was not created")

            except AudioConversionError as e:
                logger.error("✗ Conversion failed: %s", e)
            except Exception as e:
                logger.error("✗ Unexpected error: %s", e)


def test_file_size_estimation():
    """Test file size estimation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: File Size Estimation")
    logger.info("="*70)

    input_size = 10.0  # 10 MB WAV file

    estimates = [
        ("mp3", "128k"),
        ("mp3", "192k"),
        ("mp3", "320k"),
        ("flac", None),
        ("ogg", "128k"),
        ("ogg", "192k"),
        ("wav", None),
    ]

    logger.info("Input file size: %.2f MB", input_size)
    logger.info("")

    for fmt, bitrate in estimates:
        estimated_size = estimate_file_size(input_size, fmt, bitrate)
        ratio = (estimated_size / input_size) * 100
        logger.info(
            "%-8s (%-5s): %.2f MB (%.1f%% of original)",
            fmt.upper(),
            bitrate or "N/A",
            estimated_size,
            ratio
        )


def test_error_handling(wav_file: Path):
    """Test error handling for invalid inputs."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Error Handling")
    logger.info("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        error_tests = [
            ("invalid_file.wav", "mp3", None, "Non-existent input file"),
            (wav_file, "invalid_format", None, "Invalid output format"),
            (wav_file, "mp3", "256k", "Invalid bitrate for format"),
        ]

        for input_file, fmt, bitrate, description in error_tests:
            try:
                output_file = tmpdir / "test_output.mp3"
                logger.info("Testing: %s", description)

                convert_audio(
                    input_file,
                    output_file,
                    fmt,
                    bitrate=bitrate
                )
                logger.error("✗ Should have raised an error: %s", description)
            except (InvalidFormatError, InvalidBitrateError, AudioConversionError) as e:
                logger.info("✓ Correctly caught error: %s", type(e).__name__)


def test_supported_formats():
    """Display supported formats and options."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Supported Formats")
    logger.info("="*70)

    formats = get_supported_formats()

    for fmt, config in formats.items():
        logger.info("\nFormat: %s", fmt.upper())
        if config['bitrates']:
            logger.info("  Bitrates: %s", ", ".join(config['bitrates']))
            logger.info("  Default: %s", config['default'])
        else:
            logger.info("  Type: Lossless (no bitrate options)")


def main():
    """Run all tests."""
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║      Audio Format Conversion Tests (Task 2.2)         ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info("")

    try:
        # Create test WAV file (5 seconds)
        wav_file = create_test_wav(duration_seconds=5)

        # Run all tests
        test_supported_formats()
        test_format_validation()
        test_bitrate_validation()
        test_conversions(wav_file)
        test_file_size_estimation()
        test_error_handling(wav_file)

        # Cleanup
        wav_file.unlink(missing_ok=True)

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
        logger.error("Error: %s", e)
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
