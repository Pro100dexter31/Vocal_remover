import { useState, useEffect } from 'react';

function SeparationLevelSlider({ value = 50, onChange }) {
  const [intensity, setIntensity] = useState(value);

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

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Separation Level</h3>
        <span className="text-2xl font-bold text-primary-400">{intensity}%</span>
      </div>
      <p className="mb-4 text-sm text-slate-400">Vocal Level: {intensity}%</p>

      <div className="mb-4">
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

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span className="text-sm">←</span>
          More Instrumental
        </span>
        <span className="flex items-center gap-1">
          More Vocals
          <span className="text-sm">→</span>
        </span>
      </div>
    </div>
  );
}

export default SeparationLevelSlider;
