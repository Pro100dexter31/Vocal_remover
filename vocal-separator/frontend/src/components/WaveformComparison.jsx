import { useEffect, useRef, useState } from 'react';

// Okabe-Ito colorblind-safe palette (distinguishable under all common types
// of color vision deficiency). Each track also carries a text label and a
// legend dot, so color is never the only way to tell tracks apart.
const TRACKS = [
  { key: 'original', label: 'Original', color: '#94a3b8' },       // neutral gray
  { key: 'vocals', label: 'Vocals', color: '#56B4E9' },           // sky blue
  { key: 'accompaniment', label: 'Instrumental', color: '#E69F00' }, // orange
  { key: 'both', label: 'Both (Mixed)', color: '#CC79A7' },       // reddish purple
];

const BASE_WIDTH = 700;
const HEIGHT = 72;

function drawWaveform(canvas, peaks, color, playheadFraction) {
  if (!canvas || !peaks?.length) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = 'rgba(15, 23, 42, 0.6)';
  ctx.fillRect(0, 0, width, height);

  const barWidth = width / peaks.length;
  const mid = height / 2;

  ctx.fillStyle = color;
  peaks.forEach((value, i) => {
    const barHeight = Math.max(1, value * height);
    const x = i * barWidth;
    ctx.fillRect(x, mid - barHeight / 2, Math.max(1, barWidth - 0.5), barHeight);
  });

  // Center line
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();

  // Live playhead - current preview playback position, distinct from the
  // (lighter, dashed) hover cursor drawn separately as an overlay div.
  if (playheadFraction != null && playheadFraction >= 0 && playheadFraction <= 1) {
    const x = playheadFraction * width;
    ctx.strokeStyle = '#fbbf24'; // amber - stands out against all 4 track colors
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
}

function WaveformComparison({
  taskId,
  apiBaseUrl = '',
  duration = 0,
  currentTime = 0,
  onSeek = null,
}) {
  const [waveforms, setWaveforms] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ready | unavailable
  const [zoom, setZoom] = useState(1);
  const [hover, setHover] = useState(null); // { time, x }
  const canvasRefs = useRef({});
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    setStatus('loading');

    fetch(`${apiBaseUrl}/api/waveform/${taskId}`)
      .then((res) => {
        if (!res.ok) throw new Error('not available');
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        setWaveforms(data);
        setStatus('ready');
      })
      .catch(() => {
        if (!cancelled) setStatus('unavailable');
      });

    return () => {
      cancelled = true;
    };
  }, [taskId, apiBaseUrl]);

  const width = BASE_WIDTH * zoom;
  const playheadFraction = duration > 0 ? currentTime / duration : null;

  useEffect(() => {
    if (status !== 'ready' || !waveforms) return;
    TRACKS.forEach(({ key, color }) => {
      const canvas = canvasRefs.current[key];
      if (canvas) drawWaveform(canvas, waveforms[key], color, playheadFraction);
    });
  }, [status, waveforms, zoom, playheadFraction]);

  if (!taskId) return null;

  const handlePointerMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const fraction = Math.max(0, Math.min(1, x / rect.width));
    const time = fraction * duration;
    setHover({ time, x });
  };

  const handleClick = () => {
    if (hover && onSeek) onSeek(hover.time);
  };

  const formatTime = (seconds) => {
    if (!seconds || Number.isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">Before/After Waveform Comparison</h3>
        {status === 'ready' && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Zoom:</span>
            {[1, 2, 3].map((z) => (
              <button
                key={z}
                type="button"
                onClick={() => setZoom(z)}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  zoom === z
                    ? 'bg-primary-500/20 text-primary-200 ring-1 ring-primary-500/50'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {z}x
              </button>
            ))}
          </div>
        )}
      </div>

      {status === 'loading' && (
        <p className="text-sm text-slate-400">Loading waveform data...</p>
      )}

      {status === 'unavailable' && (
        <p className="text-sm text-slate-500">
          Waveform comparison isn't available for this track.
        </p>
      )}

      {status === 'ready' && waveforms && (
        <>
          <div ref={scrollRef} className="overflow-x-auto rounded-lg border border-slate-700">
            <div style={{ width: `${width}px` }}>
              {TRACKS.map(({ key, label, color }) => (
                <div key={key} className="border-b border-slate-800 last:border-b-0">
                  <div className="flex items-center gap-2 bg-slate-950/60 px-3 py-1">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs font-medium text-slate-300">{label}</span>
                  </div>
                  <div
                    className="relative cursor-crosshair"
                    onMouseMove={handlePointerMove}
                    onMouseLeave={() => setHover(null)}
                    onClick={handleClick}
                  >
                    <canvas
                      ref={(el) => (canvasRefs.current[key] = el)}
                      width={width}
                      height={HEIGHT}
                      className="block w-full"
                      style={{ height: `${HEIGHT}px` }}
                    />
                    {hover && (
                      <div
                        className="pointer-events-none absolute top-0 h-full w-px border-l border-dashed border-primary-300/70"
                        style={{ left: `${hover.x}px` }}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-3">
              <span>Scroll to explore &middot; click to seek preview</span>
              {playheadFraction != null && (
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-0.5 bg-amber-400" />
                  now playing
                </span>
              )}
            </span>
            <span className="font-mono">
              {hover ? formatTime(hover.time) : formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export default WaveformComparison;
