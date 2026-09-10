import { useEffect, useRef, useState } from 'react';

const MIN = -6;
const MAX = 6;
const POLL_MS = 3000;

function label(semitones) {
  if (semitones === 0) return 'Original (0)';
  return `${semitones > 0 ? '+' : ''}${semitones} ${Math.abs(semitones) === 1 ? 'semiton' : 'semitonuri'}`;
}

function PitchControl({ taskId, apiBaseUrl = '' }) {
  const [semitones, setSemitones] = useState(0);
  const [previewState, setPreviewState] = useState('idle'); // idle | loading | ready | error
  const [job, setJob] = useState({ semitones: 0, status: 'idle', message: '' }); // idle | processing | ready | error
  const previewAudioRef = useRef(null);
  const previewUrlRef = useRef(null);
  const debounceRef = useRef(null);
  const pollRef = useRef(null);

  // Debounced short-clip preview whenever the slider settles on a new value.
  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    if (semitones === 0) {
      setPreviewState('idle');
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      setPreviewState('loading');
      try {
        const res = await fetch(
          `${apiBaseUrl}/api/pitch-preview/${taskId}?semitones=${semitones}`,
          { method: 'POST' }
        );
        if (!res.ok) throw new Error('preview failed');
        const blob = await res.blob();
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = URL.createObjectURL(blob);
        if (previewAudioRef.current) {
          previewAudioRef.current.src = previewUrlRef.current;
          previewAudioRef.current.play().catch(() => {});
        }
        setPreviewState('ready');
      } catch {
        setPreviewState('error');
      }
    }, 400);
    return () => window.clearTimeout(debounceRef.current);
  }, [semitones, taskId, apiBaseUrl]);

  useEffect(() => () => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    window.clearTimeout(pollRef.current);
  }, []);

  const applyForDownload = async () => {
    window.clearTimeout(pollRef.current);
    if (semitones === 0) {
      setJob({ semitones: 0, status: 'ready', message: '' });
      return;
    }
    setJob({ semitones, status: 'processing', message: 'Se procesează tonalitatea...' });
    try {
      const res = await fetch(`${apiBaseUrl}/api/pitch/${taskId}?semitones=${semitones}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        setJob({ semitones, status: 'error', message: data.detail || 'Eroare la procesare.' });
        return;
      }
      if (data.status === 'completed') {
        setJob({ semitones, status: 'ready', message: '' });
        return;
      }
      const jobId = data.task_id;
      const poll = async () => {
        try {
          const sres = await fetch(`${apiBaseUrl}/api/status/${jobId}`);
          const sdata = await sres.json();
          if (sdata.status === 'SUCCESS') {
            setJob({ semitones, status: 'ready', message: '' });
            return;
          }
          if (sdata.status === 'FAILURE') {
            setJob({ semitones, status: 'error', message: sdata.error || 'Procesarea a eșuat.' });
            return;
          }
          pollRef.current = window.setTimeout(poll, POLL_MS);
        } catch (e) {
          setJob({ semitones, status: 'error', message: e.message || 'Nu pot verifica statusul.' });
        }
      };
      poll();
    } catch (e) {
      setJob({ semitones, status: 'error', message: e.message || 'Eroare la pornirea procesării.' });
    }
  };

  const downloadReady = job.status === 'ready' && job.semitones === semitones && semitones !== 0;
  const downloadUrl = `${apiBaseUrl}/api/download/${taskId}/accompaniment?pitch=${semitones}`;

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">🎹 Tonalitate minus</h3>
        <span className={`text-sm font-semibold ${semitones === 0 ? 'text-slate-400' : 'text-primary-300'}`}>
          {label(semitones)}
        </span>
      </div>

      <input
        type="range"
        min={MIN}
        max={MAX}
        step={1}
        value={semitones}
        onChange={(e) => setSemitones(parseInt(e.target.value, 10))}
        className="w-full cursor-pointer"
      />
      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>{MIN} (mai jos)</span>
        <span>0</span>
        <span>+{MAX} (mai sus)</span>
      </div>

      <div className="mt-4 rounded-lg border border-slate-600 bg-slate-800/50 p-3 text-xs">
        {previewState === 'idle' && <span className="text-slate-400">Mută slider-ul ca să auzi minusul în noua tonalitate (fragment scurt).</span>}
        {previewState === 'loading' && <span className="text-yellow-300">🔄 Se generează preview-ul...</span>}
        {previewState === 'ready' && <span className="text-green-400">▶ Preview în redare — se aude noua tonalitate</span>}
        {previewState === 'error' && <span className="text-red-400">⚠ Nu s-a putut genera preview-ul</span>}
        <audio ref={previewAudioRef} className="mt-2 w-full" controls />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={applyForDownload}
          disabled={semitones === 0 || job.status === 'processing'}
          className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-semibold hover:bg-primary-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {job.status === 'processing' ? 'Se procesează...' : 'Pregătește pentru download'}
        </button>

        {downloadReady && (
          <a
            href={downloadUrl}
            className="rounded-xl border border-primary-400/60 bg-primary-500/10 px-4 py-2.5 text-sm font-semibold text-primary-200 hover:bg-primary-500/20"
          >
            Descarcă minus ({label(semitones)})
          </a>
        )}
      </div>

      {job.status === 'error' && (
        <p className="mt-3 rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-300">{job.message}</p>
      )}

      <p className="mt-4 text-xs text-slate-500">
        💡 Se schimbă doar cheia muzicală, nu și tempo-ul. Preview-ul e un fragment scurt, de calitate redusă, pentru viteză — versiunea de download e full-length, calitate completă.
      </p>
    </div>
  );
}

export default PitchControl;
