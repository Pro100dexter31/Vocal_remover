import { useEffect, useRef, useState } from 'react';

function AudioPreviewPlayer({ taskId, apiBaseUrl = '' }) {
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
    { value: 'vocals', label: '🎤 Vocals Only', icon: '🎤' },
    { value: 'accompaniment', label: '🎸 Instrumental Only', icon: '🎸' },
    { value: 'both', label: '🎵 Both', icon: '🎵' },
  ];

  const handlePreviewTypeChange = (type) => {
    setPreviewType(type);
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handlePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeChange = (e) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const handleVolumeChange = (e) => {
    const vol = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
    setVolume(vol);
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const previewUrl = `${apiBaseUrl}/api/preview/${taskId}?file_type=${previewType}`;

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <h3 className="mb-4 text-lg font-semibold">Preview Audio</h3>

      {/* Preview Type Selector */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        {previewOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => handlePreviewTypeChange(option.value)}
            className={`rounded-lg px-3 py-3 text-sm font-medium transition-all ${
              previewType === option.value
                ? 'border-primary-400 bg-primary-500/20 text-primary-200 ring-2 ring-primary-500/50'
                : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:bg-slate-700'
            }`}
            title={option.label}
          >
            <span className="mr-1">{option.icon}</span>
            {option.value === 'both' ? 'Both' : option.value === 'vocals' ? 'Vocals' : 'Instrumental'}
          </button>
        ))}
      </div>

      {/* Audio Player */}
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
            disabled={isLoading}
            className={`flex h-12 w-12 items-center justify-center rounded-full transition-all ${
              isPlaying
                ? 'bg-primary-600 text-white hover:bg-primary-500'
                : 'bg-primary-600 text-white hover:bg-primary-500'
            } ${isLoading ? 'cursor-not-allowed opacity-50' : ''}`}
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
          />
        </div>

        {/* Status */}
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
        {isPlaying && !error && (
          <p className="text-xs text-green-400">▶ Playing {previewType}...</p>
        )}
      </div>

      {/* Info */}
      <div className="rounded-lg border border-slate-600 bg-slate-800/50 p-3">
        <p className="text-xs text-slate-400">
          <span className="font-semibold">💡 Tip:</span> Switch between Vocals, Instrumental, and Both to preview different versions before downloading.
        </p>
      </div>
    </div>
  );
}

export default AudioPreviewPlayer;
