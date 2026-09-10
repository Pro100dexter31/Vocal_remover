import { useEffect, useState } from 'react';

function SpeedControl({
  taskId,
  originalDuration = 0,
  value = 1.0,
  onSpeedChange = null,
  isProcessing = false,
  statusMessage = '',
}) {
  const [selectedSpeed, setSelectedSpeed] = useState(value);
  const [newDuration, setNewDuration] = useState(originalDuration);

  const speedOptions = [
    { value: 0.5, label: '0.5x', emoji: '🐢' },
    { value: 0.75, label: '0.75x', emoji: '🚶' },
    { value: 1.0, label: '1.0x (Normal)', emoji: '▶️' },
    { value: 1.25, label: '1.25x', emoji: '🏃' },
    { value: 1.5, label: '1.5x', emoji: '🚴' },
    { value: 2.0, label: '2.0x', emoji: '⚡' },
  ];

  // Calculate new duration when speed changes
  useEffect(() => {
    if (originalDuration > 0) {
      const calculated = Math.round(originalDuration / selectedSpeed);
      setNewDuration(calculated);
    }
  }, [selectedSpeed, originalDuration]);

  const handleSpeedChange = (speed) => {
    setSelectedSpeed(speed);
    if (onSpeedChange) {
      onSpeedChange(speed);
    }
  };

  const formatDuration = (seconds) => {
    if (seconds === 0) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s`;
    return secs === 0 ? `${mins}m` : `${mins}m ${secs}s`;
  };

  const originalFormatted = formatDuration(originalDuration);
  const newFormatted = formatDuration(newDuration);

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">⏱️ Speed Control</h3>
        {selectedSpeed !== 1.0 && (
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-primary-500" />
            <span className="text-xs font-semibold text-primary-300">
              {selectedSpeed}x
            </span>
          </div>
        )}
      </div>

      {/* Speed Buttons Grid */}
      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {speedOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => handleSpeedChange(option.value)}
            disabled={isProcessing}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
              selectedSpeed === option.value
                ? 'border-primary-400 bg-primary-500/20 text-primary-200 ring-2 ring-primary-500/50'
                : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:bg-slate-700'
            } ${
              isProcessing
                ? 'cursor-not-allowed opacity-50'
                : 'hover:cursor-pointer'
            }`}
            title={`Set speed to ${option.label}`}
          >
            <span className="mr-1">{option.emoji}</span>
            {option.label}
          </button>
        ))}
      </div>

      {/* Duration Display */}
      <div className="rounded-lg border border-slate-600 bg-slate-800/50 p-4">
        <div className="mb-2 text-xs font-semibold text-slate-400">Duration Impact:</div>

        <div className="flex items-center justify-between">
          <div className="text-left">
            <div className="text-xs text-slate-500">Original</div>
            <div className="text-lg font-bold text-slate-200">{originalFormatted}</div>
          </div>

          <div className="text-center">
            <div className="text-xl font-bold text-primary-400">→</div>
          </div>

          <div className="text-right">
            <div className="text-xs text-slate-500">At {selectedSpeed}x</div>
            <div className="text-lg font-bold text-primary-300">{newFormatted}</div>
          </div>
        </div>

        {/* Duration Change Info */}
        {selectedSpeed !== 1.0 && (
          <div className="mt-3 border-t border-slate-600 pt-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Time saved/added:</span>
              <span
                className={`text-sm font-semibold ${
                  selectedSpeed > 1.0
                    ? 'text-green-400'
                    : 'text-yellow-400'
                }`}
              >
                {selectedSpeed > 1.0
                  ? `−${formatDuration(originalDuration - newDuration)}`
                  : `+${formatDuration(newDuration - originalDuration)}`}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-4 rounded-lg border border-slate-600 bg-slate-800/50 p-3">
        <p className="text-xs text-slate-400">
          <span className="font-semibold">💡 Tip:</span> Speed control preserves pitch
          (no distortion). Perfect for language learning or music production!
        </p>
      </div>

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="mt-4 rounded-lg bg-yellow-900/30 p-3">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
            <span className="text-xs text-yellow-300">{statusMessage || 'Processing speed adjustment...'}</span>
          </div>
        </div>
      )}
      {!isProcessing && statusMessage && (
        <div className="mt-4 rounded-lg bg-red-900/30 p-3">
          <span className="text-xs text-red-300">{statusMessage}</span>
        </div>
      )}
    </div>
  );
}

export default SpeedControl;
