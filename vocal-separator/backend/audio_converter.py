"""
Audio format conversion module for converting WAV files to multiple formats.
Supports: MP3, FLAC, OGG with configurable bitrates.
"""

import logging
import os
from pathlib import Path
from typing import Literal

import soundfile as sf
from pydub import AudioSegment

LOGGER = logging.getLogger(__name__)

# Supported formats and their bitrate options
SUPPORTED_FORMATS = {
    'mp3': {'bitrates': ['128k', '192k', '320k'], 'default': '192k'},
    'flac': {'bitrates': None, 'default': None},  # Lossless, no bitrate
    'ogg': {'bitrates': ['128k', '192k'], 'default': '192k'},
    'wav': {'bitrates': None, 'default': None},  # Lossless, no bitrate
}

AudioFormat = Literal['mp3', 'flac', 'ogg', 'wav']


class AudioConversionError(Exception):
    """Raised when audio conversion fails."""

    pass


class InvalidFormatError(AudioConversionError):
    """Raised when an unsupported format is requested."""

    pass


class InvalidBitrateError(AudioConversionError):
    """Raised when an invalid bitrate is specified."""

    pass


class FileReadError(AudioConversionError):
    """Raised when the source audio file cannot be read."""

    pass


def _validate_format(output_format: str) -> AudioFormat:
    """
    Validate that the output format is supported.

    Args:
        output_format: Requested output format (mp3, flac, ogg, wav)

    Returns:
        The validated format (lowercase)

    Raises:
        InvalidFormatError: If format is not supported
    """
    fmt = output_format.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        supported = ', '.join(SUPPORTED_FORMATS.keys())
        raise InvalidFormatError(
            f"Unsupported format '{output_format}'. "
            f"Supported formats: {supported}"
        )
    return fmt


def _validate_bitrate(output_format: AudioFormat, bitrate: str | None) -> str | None:
    """
    Validate that the bitrate is valid for the given format.

    Args:
        output_format: Target audio format
        bitrate: Requested bitrate (e.g., '192k')

    Returns:
        The validated bitrate, or None for lossless formats

    Raises:
        InvalidBitrateError: If bitrate is invalid for the format
    """
    format_config = SUPPORTED_FORMATS[output_format]

    # Lossless formats don't use bitrate
    if format_config['bitrates'] is None:
        if bitrate is not None:
            LOGGER.warning(
                "Bitrate ignored for lossless format %s",
                output_format,
            )
        return None

    # Lossy formats must have valid bitrate
    if bitrate is None:
        bitrate = format_config['default']
        LOGGER.info(
            "No bitrate specified for %s, using default: %s",
            output_format,
            bitrate,
        )

    bitrate = bitrate.lower().strip()
    if bitrate not in format_config['bitrates']:
        supported = ', '.join(format_config['bitrates'])
        raise InvalidBitrateError(
            f"Invalid bitrate '{bitrate}' for {output_format}. "
            f"Supported bitrates: {supported}"
        )

    return bitrate


def _read_audio_file(input_path: Path) -> tuple:
    """
    Read audio file using appropriate library.

    Args:
        input_path: Path to input audio file

    Returns:
        Tuple of (audio_data, sample_rate)

    Raises:
        FileReadError: If file cannot be read
    """
    try:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileReadError(f"Input file not found: {input_path}")

        if not input_path.is_file():
            raise FileReadError(f"Input path is not a file: {input_path}")

        # Try reading with soundfile first (handles WAV, FLAC, OGG)
        try:
            audio_data, sample_rate = sf.read(str(input_path))
            LOGGER.info(
                "Read audio: %s (%d Hz, %.1f seconds)",
                input_path.name,
                sample_rate,
                len(audio_data) / sample_rate,
            )
            return audio_data, sample_rate
        except Exception as e:
            LOGGER.debug("soundfile read failed, trying pydub: %s", e)
            # Fallback to pydub for other formats
            audio = AudioSegment.from_file(str(input_path))
            # Convert to numpy array
            import numpy as np

            audio_array = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            audio_array /= 32768.0  # Normalize to [-1, 1]
            LOGGER.info(
                "Read audio: %s (%d Hz, %.1f seconds)",
                input_path.name,
                audio.frame_rate,
                len(audio) / 1000.0,
            )
            return audio_array, audio.frame_rate

    except FileReadError:
        raise
    except Exception as e:
        raise FileReadError(f"Failed to read audio file '{input_path}': {e}") from e


def _convert_to_mp3(
    input_path: Path,
    output_path: Path,
    bitrate: str = '192k',
) -> None:
    """
    Convert audio to MP3 format.

    Args:
        input_path: Path to input audio file
        output_path: Path to output MP3 file
        bitrate: MP3 bitrate (128k, 192k, 320k)

    Raises:
        AudioConversionError: If conversion fails
    """
    try:
        LOGGER.info("Converting to MP3 (%s)...", bitrate)
        audio = AudioSegment.from_file(str(input_path))
        audio.export(
            str(output_path),
            format='mp3',
            bitrate=bitrate,
            parameters=['-q:a', '4'],  # Quality parameter
        )
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        LOGGER.info("✓ MP3 conversion complete: %.2f MB", file_size_mb)
    except FileNotFoundError as e:
        raise AudioConversionError(f"Input file not found: {input_path}") from e
    except Exception as e:
        raise AudioConversionError(f"MP3 conversion failed: {e}") from e


def _convert_to_flac(
    input_path: Path,
    output_path: Path,
) -> None:
    """
    Convert audio to FLAC format (lossless).

    Args:
        input_path: Path to input audio file
        output_path: Path to output FLAC file

    Raises:
        AudioConversionError: If conversion fails
    """
    try:
        LOGGER.info("Converting to FLAC (lossless)...")
        audio_data, sample_rate = _read_audio_file(input_path)
        sf.write(str(output_path), audio_data, sample_rate, subtype='PCM_16')
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        LOGGER.info("✓ FLAC conversion complete: %.2f MB", file_size_mb)
    except FileReadError as e:
        raise AudioConversionError(str(e)) from e
    except Exception as e:
        raise AudioConversionError(f"FLAC conversion failed: {e}") from e


def _convert_to_ogg(
    input_path: Path,
    output_path: Path,
    bitrate: str = '192k',
) -> None:
    """
    Convert audio to OGG Vorbis format.

    Args:
        input_path: Path to input audio file
        output_path: Path to output OGG file
        bitrate: OGG bitrate (128k, 192k)

    Raises:
        AudioConversionError: If conversion fails
    """
    try:
        LOGGER.info("Converting to OGG (%s)...", bitrate)
        audio = AudioSegment.from_file(str(input_path))
        audio.export(
            str(output_path),
            format='ogg',
            bitrate=bitrate,
            parameters=['-q:a', '4'],  # Quality parameter
        )
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        LOGGER.info("✓ OGG conversion complete: %.2f MB", file_size_mb)
    except FileNotFoundError as e:
        raise AudioConversionError(f"Input file not found: {input_path}") from e
    except Exception as e:
        raise AudioConversionError(f"OGG conversion failed: {e}") from e


def _convert_to_wav(
    input_path: Path,
    output_path: Path,
) -> None:
    """
    Convert audio to WAV format.

    Args:
        input_path: Path to input audio file
        output_path: Path to output WAV file

    Raises:
        AudioConversionError: If conversion fails
    """
    try:
        LOGGER.info("Converting to WAV (lossless)...")
        audio_data, sample_rate = _read_audio_file(input_path)
        sf.write(str(output_path), audio_data, sample_rate, subtype='PCM_16')
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        LOGGER.info("✓ WAV conversion complete: %.2f MB", file_size_mb)
    except FileReadError as e:
        raise AudioConversionError(str(e)) from e
    except Exception as e:
        raise AudioConversionError(f"WAV conversion failed: {e}") from e


def convert_audio(
    input_path: str | Path,
    output_path: str | Path,
    output_format: str,
    bitrate: str | None = None,
) -> Path:
    """
    Convert audio file to specified format.

    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file
        output_format: Target format (mp3, flac, ogg, wav)
        bitrate: Bitrate for lossy formats (128k, 192k, 320k)
                 Ignored for lossless formats

    Returns:
        Path to output file

    Raises:
        InvalidFormatError: If format is not supported
        InvalidBitrateError: If bitrate is invalid
        FileReadError: If input file cannot be read
        AudioConversionError: If conversion fails

    Example:
        >>> output = convert_audio(
        ...     'vocals.wav',
        ...     'vocals.mp3',
        ...     'mp3',
        ...     bitrate='320k'
        ... )
        >>> print(output)
        Path('vocals.mp3')
    """
    # Validate inputs
    output_format = _validate_format(output_format)
    bitrate = _validate_bitrate(output_format, bitrate)

    input_path = Path(input_path)
    output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Select conversion function
    converters = {
        'mp3': _convert_to_mp3,
        'flac': _convert_to_flac,
        'ogg': _convert_to_ogg,
        'wav': _convert_to_wav,
    }

    converter = converters[output_format]

    # Perform conversion
    if output_format in ('mp3', 'ogg'):
        converter(input_path, output_path, bitrate)
    else:
        converter(input_path, output_path)

    # Verify output file was created
    if not output_path.exists():
        raise AudioConversionError(
            f"Output file was not created: {output_path}"
        )

    return output_path


def get_supported_formats() -> dict:
    """
    Get information about supported formats.

    Returns:
        Dictionary with format configurations
    """
    return SUPPORTED_FORMATS.copy()


def estimate_file_size(
    input_size_mb: float,
    output_format: AudioFormat,
    bitrate: str | None = None,
) -> float:
    """
    Estimate output file size based on input and format.

    Args:
        input_size_mb: Input file size in MB
        output_format: Target format
        bitrate: Target bitrate (for lossy formats)

    Returns:
        Estimated output size in MB
    """
    # Rough estimates based on format and bitrate
    if output_format == 'mp3':
        # MP3 bitrate to output size ratio (approximate)
        bitrate_map = {'128k': 0.15, '192k': 0.22, '320k': 0.37}
        ratio = bitrate_map.get(bitrate or '192k', 0.22)
    elif output_format == 'ogg':
        bitrate_map = {'128k': 0.15, '192k': 0.22}
        ratio = bitrate_map.get(bitrate or '192k', 0.22)
    elif output_format in ('flac', 'wav'):
        # Lossless formats are roughly 50-70% of original
        ratio = 0.6
    else:
        ratio = 1.0

    return input_size_mb * ratio
