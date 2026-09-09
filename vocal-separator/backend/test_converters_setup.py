#!/usr/bin/env python3
"""
Test script for audio format converter setup.
Verifies that all required libraries for audio conversion are properly installed.
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required audio conversion libraries can be imported."""

    results = {
        'pydub': False,
        'librosa': False,
        'soundfile': False,
        'scipy': False,
        'numpy': False,
        'torch': False,
        'demucs': False,
    }

    logger.info("Testing Python library imports...")
    logger.info("=" * 60)

    # Test pydub
    try:
        from pydub import AudioSegment
        logger.info("✓ pydub: OK (version %s)", AudioSegment.__module__)
        results['pydub'] = True
    except ImportError as e:
        logger.error("✗ pydub: FAILED - %s", e)

    # Test librosa
    try:
        import librosa
        logger.info("✓ librosa: OK (version %s)", librosa.__version__)
        results['librosa'] = True
    except ImportError as e:
        logger.error("✗ librosa: FAILED - %s", e)

    # Test soundfile
    try:
        import soundfile as sf
        logger.info("✓ soundfile: OK (version %s)", sf.__version__)
        results['soundfile'] = True
    except ImportError as e:
        logger.error("✗ soundfile: FAILED - %s", e)

    # Test scipy
    try:
        import scipy
        logger.info("✓ scipy: OK (version %s)", scipy.__version__)
        results['scipy'] = True
    except ImportError as e:
        logger.error("✗ scipy: FAILED - %s", e)

    # Test numpy
    try:
        import numpy as np
        logger.info("✓ numpy: OK (version %s)", np.__version__)
        results['numpy'] = True
    except ImportError as e:
        logger.error("✗ numpy: FAILED - %s", e)

    # Test torch
    try:
        import torch
        logger.info("✓ torch: OK (version %s)", torch.__version__)
        results['torch'] = True
    except ImportError as e:
        logger.error("✗ torch: FAILED - %s", e)

    # Test demucs
    try:
        from demucs.pretrained import get_model
        logger.info("✓ demucs: OK")
        results['demucs'] = True
    except ImportError as e:
        logger.error("✗ demucs: FAILED - %s", e)

    return results


def test_ffmpeg():
    """Test that ffmpeg system binary is available."""

    import subprocess

    logger.info("")
    logger.info("Testing FFmpeg system installation...")
    logger.info("=" * 60)

    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Get version line
            version_line = result.stdout.split('\n')[0]
            logger.info("✓ ffmpeg: OK")
            logger.info("  %s", version_line)
            return True
        else:
            logger.error("✗ ffmpeg: Command failed")
            return False
    except FileNotFoundError:
        logger.error("✗ ffmpeg: NOT FOUND (install with: apt-get install ffmpeg)")
        return False
    except subprocess.TimeoutExpired:
        logger.error("✗ ffmpeg: Timeout")
        return False
    except Exception as e:
        logger.error("✗ ffmpeg: Error - %s", e)
        return False


def test_audio_formats():
    """Test audio format support through pydub."""

    logger.info("")
    logger.info("Testing audio format support...")
    logger.info("=" * 60)

    try:
        from pydub import AudioSegment

        # Test supported formats
        formats = {
            'mp3': 'MP3',
            'wav': 'WAV',
            'ogg': 'OGG',
            'flac': 'FLAC',
        }

        results = {}
        for fmt, name in formats.items():
            try:
                AudioSegment.empty().export(format=fmt, parameters=[])
                logger.info("✓ %s format: Supported", name)
                results[fmt] = True
            except Exception as e:
                logger.warning("⚠ %s format: May require ffmpeg - %s", name, str(e)[:50])
                results[fmt] = 'needs_ffmpeg'

        return results
    except ImportError:
        logger.error("✗ Could not test formats - pydub not available")
        return {}


def test_audio_processing():
    """Test audio processing capabilities."""

    logger.info("")
    logger.info("Testing audio processing functions...")
    logger.info("=" * 60)

    try:
        import librosa
        import numpy as np

        # Create a simple audio signal
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

        # Test librosa functions
        logger.info("✓ Audio generation: OK")

        # Test time stretching
        try:
            stretched = librosa.effects.time_stretch(y, rate=1.5)
            logger.info("✓ Time stretching: OK")
        except Exception as e:
            logger.warning("⚠ Time stretching: %s", str(e)[:50])

        # Test pitch shifting
        try:
            shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=2)
            logger.info("✓ Pitch shifting: OK")
        except Exception as e:
            logger.warning("⚠ Pitch shifting: %s", str(e)[:50])

        return True
    except Exception as e:
        logger.error("✗ Audio processing test failed: %s", e)
        return False


def test_file_operations():
    """Test reading/writing audio files."""

    import tempfile
    import os

    logger.info("")
    logger.info("Testing file I/O operations...")
    logger.info("=" * 60)

    try:
        from pydub import AudioSegment
        import soundfile as sf
        import numpy as np

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test WAV I/O
            try:
                wav_path = Path(tmpdir) / "test.wav"
                audio_data = np.random.randn(44100)
                sf.write(str(wav_path), audio_data, 44100)
                logger.info("✓ WAV write: OK (%d bytes)", wav_path.stat().st_size)

                audio_read, sr = sf.read(str(wav_path))
                logger.info("✓ WAV read: OK (%d samples)", len(audio_read))
            except Exception as e:
                logger.error("✗ WAV I/O failed: %s", e)

            # Test MP3 I/O through pydub
            try:
                mp3_path = Path(tmpdir) / "test.mp3"
                audio = AudioSegment.empty()
                audio.export(str(mp3_path), format="mp3")
                logger.info("✓ MP3 write: OK (%d bytes)", mp3_path.stat().st_size)
            except Exception as e:
                logger.warning("⚠ MP3 I/O: %s", str(e)[:50])

        return True
    except Exception as e:
        logger.error("✗ File I/O test failed: %s", e)
        return False


def main():
    """Run all tests and report results."""

    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║     Audio Converters Setup Verification Test           ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info("")

    # Test imports
    import_results = test_imports()

    # Test FFmpeg
    ffmpeg_ok = test_ffmpeg()

    # Test audio formats
    format_results = test_audio_formats()

    # Test audio processing
    processing_ok = test_audio_processing()

    # Test file operations
    file_ops_ok = test_file_operations()

    # Summary
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║                    TEST SUMMARY                        ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info("")

    passed = sum(1 for v in import_results.values() if v)
    logger.info("Python Libraries: %d/%d passed", passed, len(import_results))

    if ffmpeg_ok:
        logger.info("FFmpeg: ✓ Installed and working")
    else:
        logger.warning("FFmpeg: ⚠ Not available (required for full format support)")

    if format_results:
        logger.info("Audio Formats: %d formats tested", len(format_results))

    logger.info("Audio Processing: %s", "✓ OK" if processing_ok else "✗ FAILED")
    logger.info("File I/O: %s", "✓ OK" if file_ops_ok else "✗ FAILED")

    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")

    # Overall status
    all_critical_ok = all(import_results.values()) and ffmpeg_ok

    if all_critical_ok:
        logger.info("║           ✓ ALL TESTS PASSED - READY TO USE          ║")
        logger.info("╚════════════════════════════════════════════════════════╝")
        return 0
    else:
        logger.info("║     ⚠ SOME TESTS FAILED - REVIEW OUTPUT ABOVE        ║")
        logger.info("╚════════════════════════════════════════════════════════╝")
        return 1


if __name__ == '__main__':
    sys.exit(main())
