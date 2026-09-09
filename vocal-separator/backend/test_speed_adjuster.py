"""Tests for speed adjustment using time-stretching."""

import tempfile
from pathlib import Path

import librosa
import numpy as np
import pytest
import soundfile as sf

from .speed_adjuster import (
    adjust_speed,
    get_speed_label,
    validate_speed,
    estimate_processing_duration,
    get_file_size_estimate,
    InvalidSpeedError,
    FileReadError,
    SpeedProcessingError,
    SUPPORTED_SPEEDS,
)


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple test audio file (1 second @ 22050 Hz)
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        # Generate a 440 Hz sine wave (A4 note)
        y = np.sin(2 * np.pi * 440 * t)
        # Write to file
        audio_path = Path(tmpdir) / "test_audio.wav"
        sf.write(audio_path, y, sr, subtype="PCM_16")
        yield audio_path


@pytest.fixture
def long_audio_file():
    """Create a temporary long audio file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a 10-second test audio file
        sr = 22050
        duration = 10.0
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t)
        audio_path = Path(tmpdir) / "long_audio.wav"
        sf.write(audio_path, y, sr, subtype="PCM_16")
        yield audio_path


class TestSpeedValidation:
    """Test speed validation."""

    def test_validate_supported_speeds(self):
        """Test validation of supported speeds."""
        for speed in SUPPORTED_SPEEDS.keys():
            validate_speed(speed)  # Should not raise

    def test_validate_invalid_speed(self):
        """Test validation fails for invalid speeds."""
        invalid_speeds = [0.25, 0.4, 2.5, 3.0, -1.0]
        for speed in invalid_speeds:
            with pytest.raises(InvalidSpeedError):
                validate_speed(speed)

    def test_get_speed_label(self):
        """Test speed label generation."""
        assert get_speed_label(0.5) == "0.5x"
        assert get_speed_label(1.0) == "1.0x"
        assert get_speed_label(2.0) == "2.0x"

    def test_get_speed_label_invalid(self):
        """Test speed label generation fails for invalid speeds."""
        with pytest.raises(InvalidSpeedError):
            get_speed_label(0.25)


class TestSpeedAdjustment:
    """Test speed adjustment functionality."""

    def test_adjust_speed_0_5x(self, temp_audio_file):
        """Test 0.5x speed adjustment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "slowed.wav"
            result = adjust_speed(temp_audio_file, output_path, 0.5)

            assert result["status"] == "success"
            assert result["speed"] == 0.5
            assert result["pitch_invariant"] is True
            assert output_path.exists()

            # Verify output duration is 2x input
            y_original, sr = librosa.load(temp_audio_file, sr=None)
            y_slowed, _ = librosa.load(output_path, sr=None)

            original_duration = librosa.get_duration(y=y_original, sr=sr)
            slowed_duration = librosa.get_duration(y=y_slowed, sr=sr)

            assert abs(slowed_duration / original_duration - 2.0) < 0.1

    def test_adjust_speed_2_0x(self, temp_audio_file):
        """Test 2.0x speed adjustment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sped_up.wav"
            result = adjust_speed(temp_audio_file, output_path, 2.0)

            assert result["status"] == "success"
            assert result["speed"] == 2.0
            assert result["pitch_invariant"] is True
            assert output_path.exists()

            # Verify output duration is 0.5x input
            y_original, sr = librosa.load(temp_audio_file, sr=None)
            y_sped_up, _ = librosa.load(output_path, sr=None)

            original_duration = librosa.get_duration(y=y_original, sr=sr)
            sped_up_duration = librosa.get_duration(y=y_sped_up, sr=sr)

            assert abs(sped_up_duration / original_duration - 0.5) < 0.1

    def test_adjust_speed_1_0x(self, temp_audio_file):
        """Test 1.0x speed (no change)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unchanged.wav"
            result = adjust_speed(temp_audio_file, output_path, 1.0)

            assert result["status"] == "skipped"
            assert output_path.exists()

    def test_adjust_speed_invalid_file(self):
        """Test speed adjustment fails for non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.wav"
            nonexistent = Path(tmpdir) / "nonexistent.wav"

            with pytest.raises(FileReadError):
                adjust_speed(nonexistent, output_path, 0.5)

    def test_adjust_speed_invalid_speed(self, temp_audio_file):
        """Test speed adjustment fails for invalid speed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.wav"

            with pytest.raises(InvalidSpeedError):
                adjust_speed(temp_audio_file, output_path, 0.25)

    def test_adjust_speed_long_file(self, long_audio_file):
        """Test speed adjustment on long file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "adjusted.wav"
            result = adjust_speed(long_audio_file, output_path, 1.5)

            assert result["status"] == "success"
            assert result["speed"] == 1.5
            assert output_path.exists()

            # Verify duration ratio
            y_original, sr = librosa.load(long_audio_file, sr=None)
            y_adjusted, _ = librosa.load(output_path, sr=None)

            original_duration = librosa.get_duration(y=y_original, sr=sr)
            adjusted_duration = librosa.get_duration(y=y_adjusted, sr=sr)

            ratio = adjusted_duration / original_duration
            expected_ratio = 1.0 / 1.5
            assert abs(ratio - expected_ratio) < 0.1


class TestProcessingEstimates:
    """Test processing time and size estimates."""

    def test_estimate_processing_duration(self):
        """Test processing duration estimation."""
        # Processing time is ~2x audio duration
        assert estimate_processing_duration(5.0) == 10.0
        assert estimate_processing_duration(60.0) == 120.0
        assert estimate_processing_duration(600.0) == 1200.0  # 10 minutes

    def test_get_file_size_estimate(self):
        """Test file size estimation."""
        # File size scales with duration
        original_size = 1000000  # 1 MB

        # 0.5x speed: double duration = double size
        assert get_file_size_estimate(original_size, 0.5) == 2000000

        # 1.0x speed: same
        assert get_file_size_estimate(original_size, 1.0) == 1000000

        # 2.0x speed: half duration = half size
        assert get_file_size_estimate(original_size, 2.0) == 500000


class TestPitchInvariance:
    """Test that time-stretching preserves pitch."""

    def test_pitch_preservation(self, temp_audio_file):
        """Test that pitch is preserved during speed adjustment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "adjusted.wav"
            adjust_speed(temp_audio_file, output_path, 0.75)

            # Load both files and compute spectral centroid
            y_original, sr_original = librosa.load(temp_audio_file, sr=None)
            y_adjusted, sr_adjusted = librosa.load(output_path, sr=None)

            # Spectral centroid should be similar (pitch preserved)
            centroid_original = librosa.feature.spectral_centroid(y=y_original, sr=sr_original).mean()
            centroid_adjusted = librosa.feature.spectral_centroid(y=y_adjusted, sr=sr_adjusted).mean()

            # Allow 10% difference due to resampling
            ratio = centroid_adjusted / centroid_original
            assert 0.9 < ratio < 1.1


class TestAllSpeeds:
    """Test all supported speeds."""

    @pytest.mark.parametrize("speed", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0])
    def test_all_supported_speeds(self, temp_audio_file, speed):
        """Test all supported speeds work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / f"adjusted_{speed}x.wav"
            result = adjust_speed(temp_audio_file, output_path, speed)

            if speed == 1.0:
                assert result["status"] == "skipped"
            else:
                assert result["status"] == "success"
                assert result["speed"] == speed
                assert output_path.exists()


if __name__ == "__main__":
    pytest.main([__file__])
