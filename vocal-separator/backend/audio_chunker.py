"""Chunked audio processing for large files to reduce peak RAM usage."""

import logging
from pathlib import Path
from typing import Callable, Generator

import librosa
import numpy as np
import soundfile as sf

LOGGER = logging.getLogger(__name__)


class AudioChunker:
	"""Split large audio into overlapping chunks for memory-efficient processing."""

	def __init__(
		self,
		audio_path: Path,
		chunk_duration_seconds: float = 30.0,
		overlap_seconds: float = 2.0,
		sample_rate: int | None = None,
	):
		"""
		Initialize chunker with audio metadata.

		Args:
			audio_path: Path to audio file
			chunk_duration_seconds: Size of each chunk (default 30s)
			overlap_seconds: Overlap between chunks for blending (default 2s)
			sample_rate: Optional SR; auto-detect if None
		"""
		self.audio_path = Path(audio_path)
		self.chunk_duration = chunk_duration_seconds
		self.overlap_seconds = overlap_seconds

		# Get audio info without loading full file
		info = sf.info(str(self.audio_path))
		self.sample_rate = sample_rate or info.samplerate
		self.total_frames = info.frames
		self.total_duration = self.total_frames / self.sample_rate

		self.chunk_frames = int(self.chunk_duration * self.sample_rate)
		self.overlap_frames = int(self.overlap_seconds * self.sample_rate)
		self.step_frames = self.chunk_frames - self.overlap_frames

	def should_chunk(self) -> bool:
		"""Check if audio is long enough to benefit from chunking."""
		return self.total_duration > 60.0  # Only chunk if > 60 seconds

	def iter_chunks(self) -> Generator[tuple[np.ndarray, int, int], None, None]:
		"""
		Yield overlapping audio chunks.

		Yields:
			(audio_chunk, start_frame, end_frame)
		"""
		with sf.SoundFile(str(self.audio_path)) as f:
			chunk_idx = 0
			while True:
				start_frame = chunk_idx * self.step_frames
				if start_frame >= self.total_frames:
					break

				end_frame = min(start_frame + self.chunk_frames, self.total_frames)
				f.seek(start_frame)
				chunk = f.read(end_frame - start_frame)

				if len(chunk) == 0:
					break

				yield chunk, start_frame, end_frame
				chunk_idx += 1

	@staticmethod
	def blend_chunks(
		chunk1: np.ndarray,
		chunk2: np.ndarray,
		overlap_frames: int,
	) -> np.ndarray:
		"""
		Blend two overlapping chunks using crossfade.

		Args:
			chunk1: First chunk (keep trailing overlap)
			chunk2: Second chunk (replace leading overlap)
			overlap_frames: Number of overlap frames

		Returns:
			Blended audio where overlap zone is crossfaded
		"""
		if overlap_frames <= 0 or len(chunk1) == 0 or len(chunk2) == 0:
			return np.concatenate([chunk1, chunk2])

		# Linear crossfade in overlap zone
		fade_out = np.linspace(1.0, 0.0, overlap_frames)
		fade_in = np.linspace(0.0, 1.0, overlap_frames)

		# Apply fades to overlap region (handle stereo/mono)
		if chunk1.ndim > 1:
			fade_out = fade_out[:, np.newaxis]
			fade_in = fade_in[:, np.newaxis]

		# Keep chunk1 without overlap, blend overlap zone, add chunk2
		return np.concatenate([
			chunk1[:-overlap_frames],
			chunk1[-overlap_frames:] * fade_out + chunk2[:overlap_frames] * fade_in,
			chunk2[overlap_frames:],
		])

	@staticmethod
	def normalize_chunks(chunks: list[np.ndarray]) -> list[np.ndarray]:
		"""Normalize chunk levels to prevent artifacts at boundaries."""
		if not chunks or all(len(c) == 0 for c in chunks):
			return chunks

		# Find peak across all chunks
		peak = max(np.max(np.abs(c)) for c in chunks if len(c) > 0)
		if peak == 0:
			return chunks

		# Normalize to -0.1 dB (leave headroom)
		target_level = 0.891  # -1 dB
		scale = target_level / peak

		return [c * scale for c in chunks]
