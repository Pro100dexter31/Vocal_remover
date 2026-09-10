"""Tests for audio format conversions (WAV -> MP3, FLAC, OGG)."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from .audio_converter import (
    convert_audio,
    get_supported_formats,
    estimate_file_size,
    _validate_format,
    _validate_bitrate,
    InvalidFormatError,
    InvalidBitrateError,
    AudioConversionError,
)


@pytest.fixture
def wav_file():
    """A small real WAV file (multi-tone sine wave) for conversion tests."""
    duration_seconds = 2
    sample_rate = 44100
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples)
    audio = (
        0.3 * np.sin(2 * np.pi * 440 * t)
        + 0.2 * np.sin(2 * np.pi * 880 * t)
        + 0.1 * np.sin(2 * np.pi * 220 * t)
    ).astype(np.float32)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_audio.wav"
        sf.write(str(path), audio, sample_rate)
        yield path


class TestFormatValidation:
    @pytest.mark.parametrize("fmt", ["mp3", "MP3", "flac", "ogg", "wav"])
    def test_accepts_supported_formats(self, fmt):
        assert _validate_format(fmt) == fmt.lower()

    @pytest.mark.parametrize("fmt", ["invalid", "aac", ""])
    def test_rejects_unsupported_formats(self, fmt):
        with pytest.raises(InvalidFormatError):
            _validate_format(fmt)


class TestBitrateValidation:
    @pytest.mark.parametrize("fmt,bitrate", [
        ("mp3", "128k"), ("mp3", "192k"), ("mp3", "320k"),
        ("ogg", "128k"), ("ogg", "192k"),
        ("flac", None), ("wav", None),
    ])
    def test_accepts_valid_combinations(self, fmt, bitrate):
        _validate_bitrate(_validate_format(fmt), bitrate)

    @pytest.mark.parametrize("fmt,bitrate", [
        ("mp3", "256k"),  # not an MP3 option
        ("ogg", "320k"),  # not an OGG option
    ])
    def test_rejects_invalid_combinations(self, fmt, bitrate):
        with pytest.raises(InvalidBitrateError):
            _validate_bitrate(_validate_format(fmt), bitrate)

    def test_lossless_ignores_bitrate(self):
        """flac/wav accept (and ignore) a bitrate rather than rejecting it."""
        result = _validate_bitrate(_validate_format("flac"), "192k")
        assert result is None


class TestConversions:
    @pytest.mark.parametrize("fmt,bitrate", [
        ("mp3", "128k"), ("mp3", "192k"), ("mp3", "320k"),
        ("flac", None),
        ("ogg", "128k"), ("ogg", "192k"),
        ("wav", None),
    ])
    def test_conversion_produces_valid_output(self, wav_file, fmt, bitrate, tmp_path):
        output_file = tmp_path / f"converted.{fmt}"
        result = convert_audio(wav_file, output_file, fmt, bitrate=bitrate)

        assert result.exists()
        assert result.stat().st_size > 0

        # Output must be readable back as audio with the same duration.
        data, sr = sf.read(str(result))
        original_data, original_sr = sf.read(str(wav_file))
        assert abs(len(data) / sr - len(original_data) / original_sr) < 0.1

    def test_mp3_lower_bitrate_is_smaller_file(self, wav_file, tmp_path):
        low = convert_audio(wav_file, tmp_path / "low.mp3", "mp3", bitrate="128k")
        high = convert_audio(wav_file, tmp_path / "high.mp3", "mp3", bitrate="320k")
        assert low.stat().st_size < high.stat().st_size


class TestFileSizeEstimation:
    @pytest.mark.parametrize("fmt,bitrate", [
        ("mp3", "128k"), ("mp3", "192k"), ("mp3", "320k"),
        ("flac", None), ("ogg", "128k"), ("ogg", "192k"), ("wav", None),
    ])
    def test_returns_positive_estimate(self, fmt, bitrate):
        estimate = estimate_file_size(10.0, fmt, bitrate)
        assert estimate > 0

    def test_higher_bitrate_estimates_larger_file(self):
        low = estimate_file_size(10.0, "mp3", "128k")
        high = estimate_file_size(10.0, "mp3", "320k")
        assert high > low


class TestErrorHandling:
    def test_missing_input_file_raises(self, tmp_path):
        with pytest.raises(AudioConversionError):
            convert_audio(tmp_path / "does_not_exist.wav", tmp_path / "out.mp3", "mp3")

    def test_invalid_output_format_raises(self, wav_file, tmp_path):
        with pytest.raises(InvalidFormatError):
            convert_audio(wav_file, tmp_path / "out.xyz", "invalid_format")

    def test_invalid_bitrate_raises(self, wav_file, tmp_path):
        with pytest.raises(InvalidBitrateError):
            convert_audio(wav_file, tmp_path / "out.mp3", "mp3", bitrate="256k")


class TestSupportedFormats:
    def test_returns_all_expected_formats(self):
        formats = get_supported_formats()
        assert set(formats.keys()) >= {"mp3", "flac", "ogg", "wav"}

    def test_lossy_formats_declare_bitrates(self):
        formats = get_supported_formats()
        assert formats["mp3"]["bitrates"]
        assert formats["ogg"]["bitrates"]

    def test_lossless_formats_have_no_bitrates(self):
        formats = get_supported_formats()
        assert not formats["flac"]["bitrates"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
