"""Environment sanity checks: verifies the libraries and system binaries
audio conversion depends on are actually importable/available.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_required_libraries_importable():
    """All libraries the audio pipeline depends on must be importable."""
    modules = ["pydub", "librosa", "soundfile", "scipy", "numpy", "torch"]
    failures = []

    for name in modules:
        try:
            __import__(name)
            logger.info("OK: %s", name)
        except ImportError as e:
            logger.error("FAILED: %s - %s", name, e)
            failures.append(name)

    try:
        from demucs.pretrained import get_model  # noqa: F401
        logger.info("OK: demucs")
    except ImportError as e:
        logger.error("FAILED: demucs - %s", e)
        failures.append("demucs")

    assert not failures, f"Missing required libraries: {failures}"


def test_ffmpeg_available():
    """ffmpeg must be on PATH - pydub/audio_converter shell out to it."""
    result = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, "ffmpeg is not available or not working"
    logger.info("OK: %s", result.stdout.splitlines()[0])


def test_pydub_can_export_all_formats():
    """pydub (via ffmpeg) must be able to export each format we support."""
    from pydub import AudioSegment

    for fmt in ("mp3", "wav", "ogg", "flac"):
        AudioSegment.empty().export(format=fmt)
        logger.info("OK: pydub can export %s", fmt)


def test_librosa_time_stretch_and_pitch_shift_work():
    """Sanity-check the two librosa effects the app relies on directly."""
    import librosa
    import numpy as np

    sr = 22050
    t = np.linspace(0, 1.0, sr)
    y = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    stretched = librosa.effects.time_stretch(y, rate=1.5)
    assert len(stretched) > 0

    shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=2)
    assert shifted.shape == y.shape


def test_wav_round_trip():
    """soundfile must be able to write and read back a WAV file losslessly (in shape)."""
    import numpy as np
    import soundfile as sf

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "test.wav"
        audio_data = np.random.randn(44100).astype(np.float32)
        sf.write(str(wav_path), audio_data, 44100)

        assert wav_path.stat().st_size > 0
        audio_read, sr = sf.read(str(wav_path))
        assert len(audio_read) == len(audio_data)
        assert sr == 44100


def test_mp3_export_via_pydub():
    """pydub must be able to produce a non-empty MP3 file."""
    from pydub import AudioSegment

    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = Path(tmpdir) / "test.mp3"
        AudioSegment.silent(duration=500).export(str(mp3_path), format="mp3")
        assert mp3_path.stat().st_size > 0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
