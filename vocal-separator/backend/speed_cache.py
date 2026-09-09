"""Caching system for speed-adjusted audio files."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


class SpeedCache:
    """Manages caching of speed-adjusted audio files."""

    def __init__(self, cache_dir: Path):
        """
        Initialize speed cache.

        Args:
            cache_dir: Directory to store cache metadata
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "speed_cache_index.json"

        # Load existing index
        self.index = self._load_index()

    def _load_index(self) -> dict:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    return json.load(f)
            except Exception as e:
                LOGGER.warning("Failed to load cache index: %s", e)
                return {}
        return {}

    def _save_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self.index_file, "w") as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            LOGGER.warning("Failed to save cache index: %s", e)

    def _get_cache_key(
        self, file_path: Path, file_hash: str, speed: float, file_type: str
    ) -> str:
        """
        Generate cache key for speed adjustment.

        Args:
            file_path: Path to audio file
            file_hash: Hash of file content
            speed: Speed factor
            file_type: Type of file (vocals/accompaniment)

        Returns:
            Cache key
        """
        key_str = f"{file_path.name}_{file_hash}_{speed}_{file_type}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _hash_file(self, file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_path: Path to file
            chunk_size: Chunk size for reading

        Returns:
            File hash (hex string)
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            LOGGER.warning("Failed to hash file: %s", e)
            return ""

    def get_cached_file(
        self, file_path: Path, speed: float, file_type: str
    ) -> Optional[Path]:
        """
        Get cached speed-adjusted file if available.

        Args:
            file_path: Path to original audio file
            speed: Speed factor
            file_type: Type of file (vocals/accompaniment)

        Returns:
            Path to cached file or None if not in cache
        """
        # Calculate file hash
        file_hash = self._hash_file(file_path)
        if not file_hash:
            return None

        # Get cache key
        cache_key = self._get_cache_key(file_path, file_hash, speed, file_type)

        # Check if in index
        if cache_key not in self.index:
            LOGGER.debug("Cache miss: %s", cache_key)
            return None

        cached_info = self.index[cache_key]
        cached_path = Path(cached_info["path"])

        # Verify cached file still exists
        if not cached_path.exists():
            LOGGER.warning("Cached file missing: %s", cached_path)
            del self.index[cache_key]
            self._save_index()
            return None

        LOGGER.info("Cache hit: %s (speed: %sx)", file_path.name, speed)
        return cached_path

    def cache_file(
        self,
        file_path: Path,
        speed: float,
        file_type: str,
        cached_path: Path,
        metadata: dict,
    ) -> None:
        """
        Add file to cache index.

        Args:
            file_path: Path to original audio file
            speed: Speed factor
            file_type: Type of file (vocals/accompaniment)
            cached_path: Path to cached speed-adjusted file
            metadata: Additional metadata to store
        """
        # Calculate file hash
        file_hash = self._hash_file(file_path)
        if not file_hash:
            LOGGER.warning("Could not cache file: unable to hash")
            return

        # Get cache key
        cache_key = self._get_cache_key(file_path, file_hash, speed, file_type)

        # Store in index
        self.index[cache_key] = {
            "original_path": str(file_path),
            "original_hash": file_hash,
            "speed": speed,
            "file_type": file_type,
            "path": str(cached_path),
            "cached_at": datetime.now().isoformat(),
            "size_bytes": cached_path.stat().st_size if cached_path.exists() else 0,
            **metadata,
        }

        # Save index
        self._save_index()
        LOGGER.info("Cached: %s (speed: %sx)", cached_path.name, speed)

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self.index.clear()
        self._save_index()
        LOGGER.info("Cache cleared")

    def cleanup_old_entries(self, max_entries: int = 100) -> None:
        """
        Remove oldest cache entries if exceeding max.

        Args:
            max_entries: Maximum number of cache entries
        """
        if len(self.index) <= max_entries:
            return

        # Sort by cached_at date
        sorted_entries = sorted(
            self.index.items(),
            key=lambda x: x[1].get("cached_at", ""),
        )

        # Remove oldest entries
        entries_to_remove = len(self.index) - max_entries
        for i in range(entries_to_remove):
            key = sorted_entries[i][0]
            LOGGER.info("Removing old cache entry: %s", key)
            del self.index[key]

        self._save_index()

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_size = sum(entry.get("size_bytes", 0) for entry in self.index.values())
        return {
            "total_entries": len(self.index),
            "total_size_mb": total_size / (1024 * 1024),
            "speeds": list(set(entry.get("speed") for entry in self.index.values())),
        }
