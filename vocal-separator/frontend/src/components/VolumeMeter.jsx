import { useEffect, useState } from 'react';

const METER_CONFIG = {
  minDb: -20,
  maxDb: 0,
  safeThreshold: -6,    // Green up to -6dB
  warningThreshold: -3, // Yellow from -6dB to -3dB
  dangerThreshold: 0,   // Red from -3dB to 0dB (clipping)
};

function getColorForDb(db) {
  if (db < METER_CONFIG.safeThreshold) {
    return 'from-green-500 to-green-600';    // Green - Safe
  } else if (db < METER_CONFIG.warningThreshold) {
    return 'from-yellow-500 to-yellow-600';  // Yellow - Caution
  } else {
    return 'from-red-500 to-red-600';        // Red - Danger/Clipping
  }
}

function getStatusLabel(db) {
  if (db < METER_CONFIG.safeThreshold) {
    return '✅ Safe';
  } else if (db < METER_CONFIG.warningThreshold) {
    return '⚠️ Caution';
  } else {
    return '🔴 Clipping Risk';
  }
}

function getMeterWidth(db) {
  const range = METER_CONFIG.maxDb - METER_CONFIG.minDb;
  const normalized = Math.max(0, Math.min(1, (db - METER_CONFIG.minDb) / range));
  return normalized * 100;
}

function VolumeMeter({ beforeDb = null, afterDb = null, title = 'Volume Level' }) {
  const [showComparison, setShowComparison] = useState(beforeDb !== null && afterDb !== null);

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <h3 className="mb-4 text-lg font-semibold">{title}</h3>

      {/* Before Normalization */}
      {beforeDb !== null && (
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-300">Before Normalization</p>
            <div className="text-right">
              <p className="text-lg font-bold text-slate-100">{beforeDb.toFixed(1)} dB</p>
              <p className={`text-xs font-semibold ${
                beforeDb < METER_CONFIG.safeThreshold ? 'text-green-400' :
                beforeDb < METER_CONFIG.warningThreshold ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {getStatusLabel(beforeDb)}
              </p>
            </div>
          </div>

          {/* Meter Bar */}
          <div className="mb-2 h-6 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${getColorForDb(beforeDb)} transition-all duration-300`}
              style={{ width: `${getMeterWidth(beforeDb)}%` }}
            />
          </div>

          {/* Scale */}
          <div className="flex justify-between text-xs text-slate-500">
            <span>-20 dB</span>
            <span>-10 dB</span>
            <span>0 dB</span>
          </div>
        </div>
      )}

      {/* Arrow Down */}
      {beforeDb !== null && afterDb !== null && (
        <div className="mb-6 flex justify-center">
          <div className="text-3xl text-slate-500">↓</div>
        </div>
      )}

      {/* After Normalization */}
      {afterDb !== null && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-300">After Normalization</p>
            <div className="text-right">
              <p className="text-lg font-bold text-slate-100">{afterDb.toFixed(1)} dB</p>
              <p className={`text-xs font-semibold ${
                afterDb < METER_CONFIG.safeThreshold ? 'text-green-400' :
                afterDb < METER_CONFIG.warningThreshold ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {getStatusLabel(afterDb)}
              </p>
            </div>
          </div>

          {/* Meter Bar */}
          <div className="mb-2 h-6 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${getColorForDb(afterDb)} transition-all duration-300`}
              style={{ width: `${getMeterWidth(afterDb)}%` }}
            />
          </div>

          {/* Scale */}
          <div className="flex justify-between text-xs text-slate-500">
            <span>-20 dB</span>
            <span>-10 dB</span>
            <span>0 dB</span>
          </div>

          {/* Improvement Info */}
          {beforeDb !== null && (
            <div className="mt-4 rounded-lg border border-slate-600 bg-slate-800/50 p-3">
              <p className="text-xs text-slate-400">
                <span className="font-semibold">📊 Improvement:</span>{' '}
                {(afterDb - beforeDb).toFixed(1)} dB
                {afterDb > beforeDb ? ' 📈 (louder)' : ' 📉 (quieter)'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="mt-6 space-y-2 rounded-lg border border-slate-600 bg-slate-800/50 p-3">
        <p className="mb-2 text-xs font-semibold text-slate-300">📖 Volume Guide:</p>
        <div className="space-y-1 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500" />
            <span>Safe: Below -6 dB (good headroom)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-yellow-500" />
            <span>Caution: -6 dB to -3 dB (approaching max)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500" />
            <span>Danger: -3 dB to 0 dB (clipping risk)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VolumeMeter;
