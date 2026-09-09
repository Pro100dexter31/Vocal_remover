import { useState, useEffect } from 'react';

function SeparationLevelSlider({ value = 50, onChange }) {
  const [intensity, setIntensity] = useState(value);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    setIntensity(value);
  }, [value]);

  const handleChange = (e) => {
    const newValue = parseInt(e.target.value, 10);
    setIntensity(newValue);
    if (onChange) {
      onChange(newValue);
    }
  };

  const handlePreset = (presetValue, label) => {
    setIntensity(presetValue);
    if (onChange) {
      onChange(presetValue);
    }
  };

  const getPresetLabel = () => {
    if (intensity === 0) return 'Instrumental Only';
    if (intensity === 50) return 'Balanced';
    if (intensity === 100) return 'Vocals Only';
    return null;
  };

  const presetLabel = getPresetLabel();

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">Separation Level</h3>
          <div className="relative group">
            <button
              type="button"
              className="text-slate-400 hover:text-slate-300 transition-colors"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              title="Adjust to get the perfect balance"
            >
              <span className="text-base font-bold">ℹ️</span>
            </button>
            {showTooltip && (
              <div className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-slate-800 text-slate-200 text-xs rounded-lg whitespace-nowrap border border-slate-600 z-10">
                Adjust to get the perfect balance
              </div>
            )}
          </div>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-primary-400">{intensity}%</span>
          {presetLabel && (
            <p className="text-xs text-primary-300 mt-1">{presetLabel}</p>
          )}
        </div>
      </div>
      <p className="mb-4 text-sm text-slate-400">Vocal Level: {intensity}%</p>

      <div className="mb-5">
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={intensity}
          onChange={handleChange}
          className="w-full cursor-pointer appearance-none rounded-lg bg-slate-800 bg-gradient-to-r from-slate-700 to-slate-600 outline-none accent-primary-500"
          style={{
            background: `linear-gradient(to right, rgb(15, 23, 42) 0%, rgb(59, 130, 246) ${intensity}%, rgb(30, 41, 59) ${intensity}%, rgb(30, 41, 59) 100%)`,
          }}
        />
      </div>

      <div className="mb-4 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span className="text-sm">←</span>
          More Instrumental
        </span>
        <span className="flex items-center gap-1">
          More Vocals
          <span className="text-sm">→</span>
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          onClick={() => handlePreset(0, 'Instrumental Only')}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
            intensity === 0
              ? 'bg-secondary-500 text-white shadow-lg shadow-secondary-500/50'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
          title="Pure instrumental, no vocals (0%)"
        >
          🎸 Instrumental
        </button>
        <button
          type="button"
          onClick={() => handlePreset(50, 'Balanced')}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
            intensity === 50
              ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/50'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
          title="Balanced separation (50%)"
        >
          ⚖️ Balanced
        </button>
        <button
          type="button"
          onClick={() => handlePreset(100, 'Vocals Only')}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
            intensity === 100
              ? 'bg-primary-400 text-white shadow-lg shadow-primary-400/50'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
          title="Maximum vocals (100%)"
        >
          🎤 Vocals
        </button>
      </div>
    </div>
  );
}

export default SeparationLevelSlider;
