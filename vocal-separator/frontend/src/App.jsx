import { useEffect, useRef, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const MAX_FILE_SIZE = 500 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.flac', '.ogg', '.m4a'];
const POLLING_INTERVAL = 3000;

function App() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('IDLE');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [results, setResults] = useState({ vocalsUrl: '', accompanimentUrl: '' });
  const inputRef = useRef(null);
  const pollingRef = useRef(null);

  const checkStatus = async (currentTaskId) => {
    const response = await fetch(`${API_BASE_URL}/api/status/${currentTaskId}`);
    if (!response.ok) throw new Error('Could not read processing status.');
    const data = await response.json();
    setStatus(data.status);
    setProgress(data.progress || 0);
    if (data.status === 'SUCCESS') {
      setResults({ vocalsUrl: data.vocals_url, accompanimentUrl: data.accompaniment_url });
      setLoading(false);
      return true;
    }
    if (data.status === 'FAILURE' || data.status === 'FAILED') {
      setError(data.error || 'Audio processing failed.');
      setLoading(false);
      return true;
    }
    return false;
  };

  const startPolling = (currentTaskId) => {
    window.clearTimeout(pollingRef.current);
    const poll = async () => {
      try {
        const finished = await checkStatus(currentTaskId);
        if (!finished) pollingRef.current = window.setTimeout(poll, POLLING_INTERVAL);
      } catch (pollError) {
        setError(pollError.message || 'Could not read processing status.');
        setStatus('FAILED');
        setLoading(false);
      }
    };
    poll();
  };

  useEffect(() => () => window.clearTimeout(pollingRef.current), []);

  const uploadFile = async (file) => {
    setLoading(true);
    setError('');
    setResults({ vocalsUrl: '', accompanimentUrl: '' });
    setStatus('UPLOADING');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload`, { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Upload failed.');
      setTaskId(data.task_id);
      setStatus(data.status || 'PENDING');
      startPolling(data.task_id);
    } catch (uploadError) {
      setError(uploadError.message || 'Upload failed.');
      setStatus('FAILED');
      setLoading(false);
    }
  };

  const handleFile = (file) => {
    if (!file) return;
    const extension = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setError(`Unsupported format. Use ${ALLOWED_EXTENSIONS.join(', ')}.`);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError('The file is larger than the 500 MB limit.');
      return;
    }
    setFileName(file.name);
    setProgress(0);
    uploadFile(file);
  };

  const handleDrag = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(event.type === 'dragenter' || event.type === 'dragover');
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    handleFile(event.dataTransfer.files?.[0]);
  };

  const handleFileInput = (event) => {
    handleFile(event.target.files?.[0]);
    event.target.value = '';
  };

  const handleDownload = (fileType) => {
    const source = fileType === 'vocals' ? results.vocalsUrl : results.accompanimentUrl;
    const url = source?.startsWith('http') ? source : `${API_BASE_URL}${source || ''}`;
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleReset = () => {
    window.clearTimeout(pollingRef.current);
    setTaskId(null);
    setStatus('IDLE');
    setLoading(false);
    setError('');
    setProgress(0);
    setFileName('');
    setResults({ vocalsUrl: '', accompanimentUrl: '' });
  };

  const renderUploadZone = () => (
    <div className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-14 ${dragActive ? 'border-primary-400 bg-primary-500/10' : 'border-slate-700 bg-slate-900/50'}`} onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}>
      <div className="mx-auto mb-5 text-5xl text-primary-300">◉</div>
      <h2 className="text-xl font-bold">Drop an audio file here</h2>
      <p className="mt-2 text-sm text-slate-400">MP3, WAV, FLAC, OGG or M4A, up to 500 MB</p>
      <button type="button" disabled={loading} onClick={() => inputRef.current?.click()} className="mt-7 rounded-xl bg-primary-600 px-6 py-3 font-semibold shadow-lg shadow-primary-950/40 hover:bg-primary-500">Choose audio file</button>
      <input ref={inputRef} className="hidden" type="file" accept={ALLOWED_EXTENSIONS.join(',')} onChange={handleFileInput} />
    </div>
  );

  const renderLoadingState = () => (fileName || loading || taskId) && (
    <div className="mt-6 rounded-2xl bg-slate-900/70 p-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{fileName || 'Audio task'}</p><p className="mt-1 text-xs uppercase tracking-wider text-slate-500">{status}</p></div><div className="flex items-center gap-3"><span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-primary-300" /><span className="text-2xl font-bold text-primary-300">{progress}%</span></div></div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-500" style={{ width: `${progress}%` }} /></div>
    </div>
  );

  const renderSuccessState = () => status === 'SUCCESS' && (
    <div className="mt-6 grid gap-4 sm:grid-cols-2 animate-slide-in-right">
      {[['vocals', 'Vocals stem', results.vocalsUrl], ['accompaniment', 'Accompaniment stem', results.accompanimentUrl]].map(([type, label, source]) => {
        const url = source?.startsWith('http') ? source : `${API_BASE_URL}${source || ''}`;
        return <div key={type} className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4"><p className="mb-3 font-semibold">{label}</p><audio className="mb-4 w-full" controls src={url} /><button type="button" onClick={() => handleDownload(type)} className="w-full rounded-xl bg-primary-600 px-4 py-3 font-semibold hover:bg-primary-500">Download {type}.wav</button></div>;
      })}
    </div>
  );

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 px-5 py-10 text-slate-100 sm:px-8"><div className="mx-auto max-w-4xl">
      <header className="mb-10 animate-fade-in text-center"><div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-primary-600 text-2xl shadow-glow">♫</div><p className="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-primary-300">Vocal Separator</p><h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">Find the voice inside.</h1><p className="mx-auto mt-4 max-w-xl text-base text-slate-400">Upload a track and receive clean vocal and accompaniment stems.</p></header>
      <section className="glass-effect animate-slide-in-left rounded-3xl p-5 sm:p-8">{renderUploadZone()}{error && <p role="alert" className="mt-5 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}{renderLoadingState()}{renderSuccessState()}{(status === 'SUCCESS' || status === 'FAILED') && <button type="button" onClick={handleReset} className="mt-5 text-sm font-semibold text-slate-400 underline-offset-4 hover:text-white hover:underline">Process another file</button>}</section>
      <footer className="mt-8 text-center text-sm text-slate-500">Vocal Separator · Audio processing powered by Spleeter</footer>
    </div></main>
  );
}

export default App;
