"""Tests for musical key (pitch) shifting."""

import tempfile
from pathlib import Path

import librosa
import numpy as np
import pytest
import soundfile as sf

from .pitch_shifter import (
    adjust_pitch,
    validate_semitones,
    get_semitones_label,
    InvalidSemitonesError,
    FileReadError,
    PitchProcessingError,
    MIN_SEMITONES,
    MAX_SEMITONES,
)


@pytest.fixture
def tone_file():
    """A 3-second 440 Hz sine wave — a clean signal to measure pitch shift on."""
    sr = 22050
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "tone.wav"
        sf.write(str(path), y, sr, subtype="PCM_16")
        yield path


class TestValidation:
    @pytest.mark.parametrize("n", [MIN_SEMITONES, -3, -0.5, 0, 2, MAX_SEMITONES])
    def test_accepts_in_range(self, n):
        validate_semitones(n)  # must not raise

    @pytest.mark.parametrize("n", [MIN_SEMITONES - 1, MAX_SEMITONES + 1, -12, 12, 99])
    def test_rejects_out_of_range(self, n):
        with pytest.raises(InvalidSemitonesError):
            validate_semitones(n)

    def test_label_formatting(self):
        assert get_semitones_label(0) == "0 semitones"
        assert get_semitones_label(3) == "+3 semitones"
        assert get_semitones_label(-2) == "-2 semitones"


class TestAdjustPitch:
    def test_zero_semitones_copies_unchanged(self, tone_file, tmp_path):
        out = tmp_path / "out.wav"
        result = adjust_pitch(tone_file, out, 0)
        assert result["status"] == "skipped"
        assert out.read_bytes() == tone_file.read_bytes()

    def test_out_of_range_raises_before_processing(self, tone_file, tmp_path):
        with pytest.raises(InvalidSemitonesError):
            adjust_pitch(tone_file, tmp_path / "out.wav", 99)

    def test_missing_input_raises_file_read_error(self, tmp_path):
        with pytest.raises(FileReadError):
            adjust_pitch(tmp_path / "nope.wav", tmp_path / "out.wav", 2)

    def test_duration_is_preserved(self, tone_file, tmp_path):
        out = tmp_path / "out.wav"
        adjust_pitch(tone_file, out, 4)
        y_in, sr_in = librosa.load(tone_file, sr=None)
        y_out, sr_out = librosa.load(out, sr=None)
        d_in = librosa.get_duration(y=y_in, sr=sr_in)
        d_out = librosa.get_duration(y=y_out, sr=sr_out)
        assert abs(d_in - d_out) < 0.05  # tempo unchanged

    def test_pitch_actually_shifts_up(self, tone_file, tmp_path):
        """A +6 semitone shift of a 440 Hz tone should land near 622 Hz."""
        out = tmp_path / "out.wav"
        adjust_pitch(tone_file, out, MAX_SEMITONES)
        y, sr = librosa.load(out, sr=None)
        f0 = librosa.yin(y, fmin=200, fmax=1200, sr=sr)
        median_f0 = float(np.median(f0))
        expected = 440 * (2 ** (MAX_SEMITONES / 12))  # ~622 Hz
        assert abs(median_f0 - expected) / expected < 0.06

    def test_pitch_actually_shifts_down(self, tone_file, tmp_path):
        out = tmp_path / "out.wav"
        adjust_pitch(tone_file, out, -5)
        y, sr = librosa.load(out, sr=None)
        f0 = librosa.yin(y, fmin=150, fmax=900, sr=sr)
        median_f0 = float(np.median(f0))
        expected = 440 * (2 ** (-5 / 12))  # ~330 Hz
        assert abs(median_f0 - expected) / expected < 0.06

    def test_preview_mode_truncates_output(self, tmp_path):
        """With max_duration_seconds set, only that much audio is processed."""
        sr = 22050
        y = (0.3 * np.sin(2 * np.pi * 440 * np.arange(sr * 10) / sr)).astype(np.float32)
        src = tmp_path / "long.wav"
        sf.write(str(src), y, sr, subtype="PCM_16")

        out = tmp_path / "clip.wav"
        adjust_pitch(src, out, 3, max_duration_seconds=4.0)

        y_out, sr_out = librosa.load(out, sr=None)
        assert librosa.get_duration(y=y_out, sr=sr_out) < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
