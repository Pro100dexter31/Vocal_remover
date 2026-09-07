import { useEffect, useRef, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const MAX_FILE_SIZE = 500 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.flac', '.ogg', '.m4a'];
const POLL_INTERVAL_MS = 1500;

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
	const pollRef = useRef(null);

	useEffect(() => () => window.clearTimeout(pollRef.current), []);

	const startPolling = (nextTaskId) => {
		window.clearTimeout(pollRef.current);
		const poll = async () => {
			try {
				const response = await fetch(`${API_BASE_URL}/api/status/${nextTaskId}`);
				if (!response.ok) throw new Error('Could not read processing status.');
				const data = await response.json();
				setStatus(data.status);
				setProgress(data.progress || 0);
				if (data.status === 'SUCCESS') {
					setResults({ vocalsUrl: data.vocals_url, accompanimentUrl: data.accompaniment_url });
					setLoading(false);
					return;
				}
				if (data.status === 'FAILURE' || data.status === 'FAILED') {
					setError(data.error || 'Audio processing failed.');
					setLoading(false);
					return;
				}
				pollRef.current = window.setTimeout(poll, POLL_INTERVAL_MS);
			} catch (pollError) {
				setError(pollError.message || 'Could not read processing status.');
				setLoading(false);
			}
		};
		poll();
	};

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

	const reset = () => {
		window.clearTimeout(pollRef.current);
		setTaskId(null);
		setStatus('IDLE');
		setLoading(false);
		setError('');
		setProgress(0);
		setFileName('');
		setResults({ vocalsUrl: '', accompanimentUrl: '' });
	};

	const downloadUrl = (url) => (url?.startsWith('http') ? url : `${API_BASE_URL}${url || ''}`);

	return (
		<main className="min-h-screen overflow-hidden bg-slate-950 px-5 py-10 text-slate-100 sm:px-8">
			<div className="mx-auto max-w-4xl">
				<header className="mb-10 animate-fade-in text-center">
					<div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-primary-600 text-2xl shadow-glow">♫</div>
					<p className="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-primary-300">Vocal Separator</p>
					<h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">Find the voice inside.</h1>
					<p className="mx-auto mt-4 max-w-xl text-base text-slate-400">Upload a track and receive clean vocal and accompaniment stems.</p>
				</header>

				<section className="glass-effect animate-slide-in-left rounded-3xl p-5 sm:p-8">
					<div
						className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-14 ${dragActive ? 'border-primary-400 bg-primary-500/10' : 'border-slate-700 bg-slate-900/50'}`}
						onDragEnter={handleDrag}
						onDragOver={handleDrag}
						onDragLeave={handleDrag}
						onDrop={handleDrop}
					>
						<div className="mx-auto mb-5 text-5xl text-primary-300">◉</div>
						<h2 className="text-xl font-bold">Drop an audio file here</h2>
						<p className="mt-2 text-sm text-slate-400">MP3, WAV, FLAC, OGG or M4A, up to 500 MB</p>
						<button type="button" disabled={loading} onClick={() => inputRef.current?.click()} className="mt-7 rounded-xl bg-primary-600 px-6 py-3 font-semibold shadow-lg shadow-primary-950/40 hover:bg-primary-500">
							Choose audio file
						</button>
						<input ref={inputRef} className="hidden" type="file" accept={ALLOWED_EXTENSIONS.join(',')} onChange={handleFileInput} />
					</div>

					{error && <p role="alert" className="mt-5 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}

					{(fileName || loading || taskId) && (
						<div className="mt-6 rounded-2xl bg-slate-900/70 p-5 animate-fade-in">
							<div className="flex flex-wrap items-center justify-between gap-3">
								<div><p className="font-semibold">{fileName || 'Audio task'}</p><p className="mt-1 text-xs uppercase tracking-wider text-slate-500">{status}</p></div>
								<span className="text-2xl font-bold text-primary-300">{progress}%</span>
							</div>
							<div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-500" style={{ width: `${progress}%` }} /></div>
						</div>
					)}

					{status === 'SUCCESS' && (
						<div className="mt-6 grid gap-3 sm:grid-cols-2 animate-slide-in-right">
							<a className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-4 font-semibold text-emerald-200 hover:bg-emerald-500/20" href={downloadUrl(results.vocalsUrl)}>Download vocals.wav</a>
							<a className="rounded-xl border border-primary-400/30 bg-primary-500/10 px-4 py-4 font-semibold text-primary-200 hover:bg-primary-500/20" href={downloadUrl(results.accompanimentUrl)}>Download accompaniment.wav</a>
						</div>
					)}
					{(status === 'SUCCESS' || status === 'FAILED') && <button type="button" onClick={reset} className="mt-5 text-sm font-semibold text-slate-400 underline-offset-4 hover:text-white hover:underline">Process another file</button>}
				</section>
			</div>
		</main>
	);
}

export default App;
