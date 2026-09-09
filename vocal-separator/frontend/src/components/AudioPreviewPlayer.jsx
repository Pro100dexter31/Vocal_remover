import { useEffect, useRef, useState } from 'react';

function AudioPreviewPlayer({
  taskId,
  apiBaseUrl = '',
  onPlayStart = null,  // Callback when playback starts (for Task 4.4)
  onPlayStop = null,   // Callback when playback stops (for Task 4.4)
  isActive = false,    // Is this player the active one (for Task 4.4)
}) {
  const [previewType, setPreviewType] = useState('both');
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [error, setError] = useState('');
  const audioRef = useRef(null);

  if (!taskId) {
    return null;
  }

  const previewOptions = [
    { value: 'vocals', label: 'Preview Vocals', emoji: '🎤' },
    { value: 'accompaniment', label: 'Preview Instrumental', emoji: '🎸' },
    { value: 'both', label: 'Preview Both (Mixed)', emoji: '🎵' },
  ];

  // Handle changes in preview type
  const handlePreviewTypeChange = (type) => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      if (onPlayStop) onPlayStop();
    }
    setPreviewType(type);
  };

  // Handle play/pause
  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      if (onPlayStop) onPlayStop();
    } else {
      // Notify parent that this player is starting playback
      if (onPlayStart) onPlayStart();

      audioRef.current.play().catch((err) => {
        console.error('Playback error:', err);
        setError('Could not start playback');
      });
      setIsPlaying(true);
    }
  };

  // Handle seeking
  const handleTimeChange = (e) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Handle volume change
  const handleVolumeChange = (e) => {
    const vol = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
    setVolume(vol);
  };

  // Format time display
  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const previewUrl = `${apiBaseUrl}/api/preview/${taskId}?file_type=${previewType}`;

  return (
    <div className={`rounded-2xl border p-6 transition-all ${
      isActive && isPlaying
        ? 'border-primary-400 bg-primary-500/10 shadow-lg shadow-primary-500/20'
        : 'border-slate-700 bg-slate-900/70'
    }`}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Preview Audio</h3>
        {isActive && isPlaying && (
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-primary-500" />
            <span className="text-xs font-semibold text-primary-300">Now Playing</span>
          </div>
        )}
      </div>

      {/* Preview Type Selector (3 Buttons - Task 4.3) */}
      <div className="mb-6 space-y-2">
        {previewOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => handlePreviewTypeChange(option.value)}
            className={`w-full rounded-lg px-4 py-3 text-sm font-medium transition-all ${
              previewType === option.value
                ? 'border-primary-400 bg-primary-500/20 text-primary-200 ring-2 ring-primary-500/50'
                : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:bg-slate-700'
            }`}
            title={option.label}
          >
            <span className="mr-2">{option.emoji}</span>
            {option.label}
          </button>
        ))}
      </div>

      {/* Audio Player - Task 4.3 */}
      <div className="mb-6 rounded-lg border border-slate-600 bg-slate-800/50 p-4">
        {/* Hidden Audio Element */}
        <audio
          ref={audioRef}
          src={previewUrl}
          onLoadedMetadata={(e) => {
            setDuration(e.target.duration);
            setError('');
          }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
          onEnded={() => {
            setIsPlaying(false);
            if (onPlayStop) onPlayStop();
          }}
          onError={(e) => {
            setError('Could not load audio preview');
            setIsPlaying(false);
          }}
          crossOrigin="anonymous"
        />

        {/* Controls */}
        <div className="mb-4 flex items-center justify-between gap-4">
          {/* Play/Pause Button */}
          <button
            onClick={handlePlayPause}
            disabled={isLoading || !isActive}
            className={`flex h-12 w-12 items-center justify-center rounded-full text-lg font-bold transition-all ${
              isActive
                ? isPlaying
                  ? 'bg-primary-600 text-white hover:bg-primary-500'
                  : 'bg-primary-600 text-white hover:bg-primary-500'
                : 'cursor-not-allowed bg-slate-700 text-slate-500 opacity-50'
            }`}
            title={isActive ? 'Play/Pause' : 'Select this preview to play'}
          >
            {isLoading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-white" />
            ) : isPlaying ? (
              '⏸'
            ) : (
              '▶'
            )}
          </button>

          {/* Time Display */}
          <div className="text-sm font-mono text-slate-300">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          {/* Volume Control */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">🔊</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={handleVolumeChange}
              className="w-20 cursor-pointer"
              disabled={!isActive}
            />
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-2">
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleTimeChange}
            className="w-full cursor-pointer"
            disabled={!isActive}
          />
        </div>

        {/* Status */}
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
        {isPlaying && !error && isActive && (
          <p className="text-xs text-green-400">▶ Playing {previewType}...</p>
        )}
        {!isActive && (
          <p className="text-xs text-slate-500">Click play to activate this preview</p>
        )}
      </div>

      {/* Info */}
      <div className="rounded-lg border border-slate-600 bg-slate-800/50 p-3">
        <p className="text-xs text-slate-400">
          <span className="font-semibold">💡 Tip:</span> Only one preview can play at a time. Select different buttons to switch preview types.
        </p>
      </div>
    </div>
  );
}

export default AudioPreviewPlayer;
