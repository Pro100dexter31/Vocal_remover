"""Downsampled waveform data generation for visual before/after comparison."""

import json
import logging
from pathlib import Path

import numpy as np

LOGGER = logging.getLogger(__name__)

DEFAULT_NUM_POINTS = 800


def generate_waveform_peaks(audio: np.ndarray, num_points: int = DEFAULT_NUM_POINTS) -> list[float]:
	"""
	Downsample audio into a fixed number of RMS points for lightweight
	waveform rendering, regardless of the track's original length.

	Args:
		audio: Audio samples, mono (1D) or multi-channel (channels, samples)
		num_points: Number of output points (canvas-width independent of duration)

	Returns:
		List of RMS values (0.0-1.0 range) with length == num_points
	"""
	if audio.ndim > 1:
		audio = audio.mean(axis=0)

	total_samples = audio.shape[-1]
	if total_samples == 0:
		return [0.0] * num_points

	chunk_size = max(1, total_samples // num_points)
	peaks: list[float] = []

	for i in range(num_points):
		start = i * chunk_size
		if start >= total_samples:
			peaks.append(0.0)
			continue
		end = min(start + chunk_size, total_samples)
		chunk = audio[start:end]
		rms = float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0
		peaks.append(round(min(rms, 1.0), 4))

	return peaks


def save_waveform_data(output_dir: Path, waveforms: dict[str, list[float]]) -> Path:
	"""Write waveform peaks for all stems to a single JSON file next to the stems."""
	path = output_dir / "waveforms.json"
	with path.open("w") as f:
		json.dump({"num_points": DEFAULT_NUM_POINTS, **waveforms}, f)
	LOGGER.info("Saved waveform data: %s", path)
	return path


def load_waveform_data(output_dir: Path) -> dict | None:
	"""Read previously generated waveform data, or None if not available."""
	path = output_dir / "waveforms.json"
	if not path.is_file():
		return None
	try:
		with path.open() as f:
			return json.load(f)
	except Exception as e:
		LOGGER.warning("Failed to read waveform data %s: %s", path, e)
		return None
