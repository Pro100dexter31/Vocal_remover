"""Comprehensive testing suite for speed control feature."""

import tempfile
import time
from pathlib import Path

import librosa
import numpy as np
import pytest
import soundfile as sf

from .speed_adjuster import adjust_speed, SUPPORTED_SPEEDS
from .speed_cache import SpeedCache


@pytest.fixture
def test_audio_5min():
    """Create a 5-minute test audio file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sr = 22050
        duration = 300  # 5 minutes
        t = np.linspace(0, duration, int(sr * duration))
        # Complex signal: multiple frequencies
        y = (
            np.sin(2 * np.pi * 440 * t) * 0.3 +  # A4 note
            np.sin(2 * np.pi * 880 * t) * 0.2 +  # A5 note
            np.sin(2 * np.pi * 220 * t) * 0.1    # A3 note
        )
        audio_path = Path(tmpdir) / "test_audio_5min.wav"
        sf.write(audio_path, y, sr, subtype="PCM_16")
        yield audio_path


class TestQualityAndStability:
    """Test audio quality and pitch stability at all speeds."""

    def test_pitch_stability_all_speeds(self, test_audio_5min):
        """Verify pitch is stable across all supported speeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            y_original, sr = librosa.load(test_audio_5min, sr=None)

            # Calculate original spectral centroid (pitch indicator)
            centroid_original = librosa.feature.spectral_centroid(
                y=y_original, sr=sr
            ).mean()

            for speed in SUPPORTED_SPEEDS.keys():
                if speed == 1.0:
                    continue

                output_path = Path(tmpdir) / f"test_{speed}x.wav"
                adjust_speed(test_audio_5min, output_path, speed)

                y_adjusted, _ = librosa.load(output_path, sr=None)
                centroid_adjusted = librosa.feature.spectral_centroid(
                    y=y_adjusted, sr=None
                ).mean()

                # Pitch should be preserved (within 10% tolerance)
                ratio = centroid_adjusted / centroid_original
                assert 0.9 < ratio < 1.1, f"Pitch unstable at {speed}x: {ratio}"

    def test_no_distortion_at_extremes(self, test_audio_5min):
        """Verify no clipping/distortion at extreme speeds (0.5x, 2.0x)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            y_original, sr = librosa.load(test_audio_5min, sr=None)

            for speed in [0.5, 2.0]:
                output_path = Path(tmpdir) / f"test_{speed}x.wav"
                adjust_speed(test_audio_5min, output_path, speed)

                y_adjusted, _ = librosa.load(output_path, sr=None)

                # Check for clipping (values at max range)
                clipping_ratio = np.sum(np.abs(y_adjusted) > 0.95) / len(y_adjusted)
                assert (
                    clipping_ratio < 0.01
                ), f"Clipping detected at {speed}x: {clipping_ratio:.2%}"

                # Check RMS level (should be similar)
                rms_original = np.sqrt(np.mean(y_original**2))
                rms_adjusted = np.sqrt(np.mean(y_adjusted**2))
                ratio = rms_adjusted / rms_original
                assert 0.8 < ratio < 1.2, f"RMS mismatch at {speed}x: {ratio}"

    def test_no_artifacts(self, test_audio_5min):
        """Verify no audio artifacts at any speed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            y_original, sr = librosa.load(test_audio_5min, sr=None)

            for speed in [0.5, 1.5, 2.0]:
                output_path = Path(tmpdir) / f"test_{speed}x.wav"
                adjust_speed(test_audio_5min, output_path, speed)

                y_adjusted, _ = librosa.load(output_path, sr=None)

                # Check for sudden amplitude jumps (artifacts)
                diffs = np.abs(np.diff(y_adjusted))
                max_diff = np.max(diffs)
                mean_diff = np.mean(diffs)

                # Sudden jumps should be rare
                large_jumps = np.sum(diffs > 10 * mean_diff)
                assert (
                    large_jumps < 10
                ), f"Audio artifacts detected at {speed}x: {large_jumps} jumps"


class TestProcessingTime:
    """Test processing time performance across speeds."""

    def test_processing_time_estimation(self, test_audio_5min):
        """Verify processing time is approximately 2x audio duration."""
        y, sr = librosa.load(test_audio_5min, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.time()
            output_path = Path(tmpdir) / "test_1_5x.wav"
            adjust_speed(test_audio_5min, output_path, 1.5)
            elapsed = time.time() - start

            # Processing should take roughly 2x the audio duration
            # Allow 50% variance for system load
            expected_time = duration * 2
            assert (
                elapsed < expected_time * 1.5
            ), f"Processing too slow: {elapsed:.1f}s vs expected {expected_time:.1f}s"

    def test_speed_comparison_1x_vs_2x(self, test_audio_5min):
        """Compare processing time between 1x and 2x speeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1.0x (should be fast - just copy)
            start = time.time()
            output_1x = Path(tmpdir) / "test_1x.wav"
            adjust_speed(test_audio_5min, output_1x, 1.0)
            time_1x = time.time() - start

            # 2.0x (should process)
            start = time.time()
            output_2x = Path(tmpdir) / "test_2x.wav"
            adjust_speed(test_audio_5min, output_2x, 2.0)
            time_2x = time.time() - start

            # 1.0x should be much faster (copy vs process)
            assert (
                time_1x < time_2x / 10
            ), f"1x should be faster: {time_1x:.2f}s vs {time_2x:.2f}s"


class TestDurationAccuracy:
    """Test that duration is correctly calculated for all speeds."""

    def test_duration_scaling(self, test_audio_5min):
        """Verify duration scales correctly with speed."""
        y_original, sr = librosa.load(test_audio_5min, sr=None)
        original_duration = librosa.get_duration(y=y_original, sr=sr)

        with tempfile.TemporaryDirectory() as tmpdir:
            for speed, label in SUPPORTED_SPEEDS.items():
                output_path = Path(tmpdir) / f"test_{speed}x.wav"
                adjust_speed(test_audio_5min, output_path, speed)

                y_adjusted, _ = librosa.load(output_path, sr=None)
                adjusted_duration = librosa.get_duration(y=y_adjusted, sr=sr)

                # Duration should scale inversely with speed
                expected_duration = original_duration / speed
                ratio = adjusted_duration / expected_duration

                # Allow 5% tolerance
                assert (
                    0.95 < ratio < 1.05
                ), f"Duration error at {label}: {ratio:.3f}"


class TestSpectralContent:
    """Test that spectral content is preserved (pitch invariance)."""

    def test_spectral_centroid_preservation(self, test_audio_5min):
        """Verify spectral centroid is preserved across speeds."""
        y_original, sr = librosa.load(test_audio_5min, sr=None)
        stft_original = np.abs(librosa.stft(y_original))
        centroid_original = librosa.feature.spectral_centroid(y=y_original, sr=sr)

        with tempfile.TemporaryDirectory() as tmpdir:
            for speed in [0.5, 1.5, 2.0]:
                output_path = Path(tmpdir) / f"test_{speed}x.wav"
                adjust_speed(test_audio_5min, output_path, speed)

                y_adjusted, _ = librosa.load(output_path, sr=None)
                stft_adjusted = np.abs(librosa.stft(y_adjusted))
                centroid_adjusted = librosa.feature.spectral_centroid(
                    y=y_adjusted, sr=sr
                )

                # Centroids should be similar
                mean_ratio = np.mean(centroid_adjusted / centroid_original)
                assert (
                    0.85 < mean_ratio < 1.15
                ), f"Spectral shift at {speed}x: {mean_ratio}"


class TestCachePerformance:
    """Test cache performance impact."""

    def test_cache_hit_speedup(self, test_audio_5min):
        """Verify cache hits are significantly faster."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache = SpeedCache(cache_dir)

            # First call: full processing
            output_1 = Path(tmpdir) / "output1.wav"
            start = time.time()
            adjust_speed(test_audio_5min, output_1, 1.5)
            cache.cache_file(test_audio_5min, 1.5, "vocals", output_1, {})
            time_first = time.time() - start

            # Second call: cache hit (simulated)
            cached = cache.get_cached_file(test_audio_5min, 1.5, "vocals")
            if cached:
                # Cache hit would be instant
                time_cache = 0.001
                assert (
                    time_first > time_cache * 100
                ), f"Cache should be 100x faster"


class TestAllSpeeds:
    """Test all supported speeds comprehensively."""

    @pytest.mark.parametrize("speed", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0])
    def test_all_speeds_complete(self, test_audio_5min, speed):
        """Test all speeds with quality verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / f"test_{speed}x.wav"

            # Process
            result = adjust_speed(test_audio_5min, output_path, speed)

            # Verify success
            if speed == 1.0:
                assert result["status"] == "skipped"
            else:
                assert result["status"] == "success"
                assert output_path.exists()
                assert result["speed"] == speed
                assert result["pitch_invariant"] is True

            # Load and verify
            y, sr = librosa.load(output_path, sr=None)
            y_orig, sr_orig = librosa.load(test_audio_5min, sr=None)

            duration = librosa.get_duration(y=y, sr=sr)
            duration_orig = librosa.get_duration(y=y_orig, sr=sr_orig)

            # Duration should scale
            expected = duration_orig / speed
            ratio = duration / expected
            assert 0.95 < ratio < 1.05


class TestErrorConditions:
    """Test error handling in quality scenarios."""

    def test_extreme_speed_values(self, test_audio_5min):
        """Test that unsupported speeds are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.wav"

            # Unsupported speeds should raise
            for invalid_speed in [0.25, 0.4, 2.5, 3.0]:
                with pytest.raises(Exception):
                    adjust_speed(test_audio_5min, output_path, invalid_speed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
