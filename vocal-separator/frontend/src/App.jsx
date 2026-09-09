import { useEffect, useRef, useState } from 'react';
import SeparationLevelSlider from './components/SeparationLevelSlider';
import FormatSelector from './components/FormatSelector';
import AudioPreviewPlayer from './components/AudioPreviewPlayer';
import SpeedControl from './components/SpeedControl';

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
  const [separationLevel, setSeparationLevel] = useState(50);
  const [selectedFormat, setSelectedFormat] = useState('wav');
  const [selectedBitrate, setSelectedBitrate] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState({});
  const [fileSize, setFileSize] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const [normalize, setNormalize] = useState(true);
  const [speed, setSpeed] = useState(1.0);  // Task 5.4: Speed control
  const [activePreviewPlayer, setActivePreviewPlayer] = useState(null);  // Task 4.4: Track active player
  const [audioDuration, setAudioDuration] = useState(0);  // Track original duration
  const inputRef = useRef(null);
  const pollingRef = useRef(null);
  const abortControllerRef = useRef(new AbortController());

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

  useEffect(() => {
    try {
      const savedLevel = localStorage.getItem('separationLevel');
      if (savedLevel) {
        const level = parseInt(savedLevel, 10);
        if (level >= 0 && level <= 100) {
          setSeparationLevel(level);
        }
      }
      const savedNormalize = localStorage.getItem('normalize');
      if (savedNormalize) {
        setNormalize(JSON.parse(savedNormalize));
      }
      const lastUploadTime = localStorage.getItem('lastUploadTime');
      if (lastUploadTime) {
        const timeDiff = Date.now() - parseInt(lastUploadTime, 10);
        const oneWeek = 7 * 24 * 60 * 60 * 1000;
        if (timeDiff > oneWeek) {
          localStorage.removeItem('separationLevel');
          localStorage.removeItem('normalize');
        }
      }
    } catch (e) {
      console.warn('Could not load preferences from localStorage:', e);
    }
    return () => window.clearTimeout(pollingRef.current);
  }, []);

  const uploadFile = async (file) => {
    setLoading(true);
    setError('');
    setResults({ vocalsUrl: '', accompanimentUrl: '' });
    setStatus('UPLOADING');
    try {
      localStorage.setItem('lastUploadTime', Date.now().toString());
      localStorage.setItem('lastUploadFile', file.name);
    } catch (e) {
      console.warn('Could not save upload info to localStorage:', e);
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('separation_intensity', separationLevel / 100);
    formData.append('normalize', normalize.toString());

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const uploadPercent = Math.round((e.loaded / e.total) * 100);
          setProgress(uploadPercent);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            setTaskId(data.task_id);
            setStatus(data.status || 'PENDING');
            setProgress(100);
            startPolling(data.task_id);
            resolve();
          } catch (e) {
            reject(new Error('Upload failed: Server did not return valid JSON'));
          }
        } else {
          try {
            const data = JSON.parse(xhr.responseText);
            reject(new Error(data.detail || `Upload failed (${xhr.status})`));
          } catch {
            reject(new Error(`Upload failed (${xhr.status})`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      xhr.open('POST', `${API_BASE_URL}/api/upload`);
      xhr.send(formData);
    }).catch((uploadError) => {
      setError(uploadError.message || 'Upload failed.');
      setStatus('FAILED');
      setLoading(false);
    });
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
    setFileSize(file.size / (1024 * 1024));
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

  const getConversionProgress = (format, fileSizeMb) => {
    const timePerMb = {
      mp3: 0.4,
      flac: 0.15,
      ogg: 0.35,
      wav: 0.01,
    };

    const totalSeconds = fileSizeMb * (timePerMb[format] || 0.3);
    const startTime = Date.now();

    return {
      totalSeconds,
      startTime,
      getProgress: () => {
        const elapsed = (Date.now() - startTime) / 1000;
        return Math.min(95, Math.round((elapsed / totalSeconds) * 100));
      },
    };
  };

  const handleDownload = async (fileType, retryCount = 0) => {
    const MAX_RETRIES = 2;
    const key = `${fileType}-${selectedFormat}-${selectedBitrate || 'default'}`;

    try {
      setIsExporting(true);
      setExportError('');

      abortControllerRef.current = new AbortController();

      const progressTracker = getConversionProgress(selectedFormat, fileSize);
      const progressInterval = setInterval(() => {
        const pct = progressTracker.getProgress();
        setDownloadProgress((prev) => ({ ...prev, [key]: pct }));
      }, 500);

      const params = new URLSearchParams({
        file_type: fileType,
        output_format: selectedFormat,
      });

      if (selectedBitrate && (selectedFormat === 'mp3' || selectedFormat === 'ogg')) {
        params.append('bitrate', selectedBitrate);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/export/${taskId}?${params}`,
        {
          method: 'POST',
          signal: abortControllerRef.current.signal,
        }
      );

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Export failed' }));
        throw new Error(errorData.detail || `Export failed (${response.status})`);
      }

      setDownloadProgress((prev) => ({ ...prev, [key]: 100 }));

      const blob = await response.blob();
      const filename = response.headers
        .get('content-disposition')
        ?.split('filename="')[1]
        ?.split('"')[0] || `${fileType}.${selectedFormat}`;

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);

      setTimeout(() => {
        setDownloadProgress((prev) => {
          const newState = { ...prev };
          delete newState[key];
          return newState;
        });
      }, 2000);

      setIsExporting(false);
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Export cancelled');
        return;
      }

      if (retryCount < MAX_RETRIES) {
        setExportError(`Export failed, retrying... (${retryCount + 1}/${MAX_RETRIES})`);
        setTimeout(() => handleDownload(fileType, retryCount + 1), 2000);
      } else {
        setExportError(err.message || 'Export failed. Please try again.');
        setIsExporting(false);
      }
    }
  };

  const handleReset = () => {
    window.clearTimeout(pollingRef.current);
    abortControllerRef.current?.abort();
    setTaskId(null);
    setStatus('IDLE');
    setLoading(false);
    setError('');
    setProgress(0);
    setFileName('');
    setResults({ vocalsUrl: '', accompanimentUrl: '' });
    setSeparationLevel(50);
    setDownloadProgress({});
    setIsExporting(false);
    setExportError('');
  };

  const renderUploadZone = () => (
    <>
      <div className="mb-6">
        <SeparationLevelSlider
          value={separationLevel}
          onChange={(newLevel) => {
            setSeparationLevel(newLevel);
            try {
              localStorage.setItem('separationLevel', newLevel.toString());
            } catch (e) {
              console.warn('Could not save separation level to localStorage:', e);
            }
          }}
        />
      </div>

      <div className="mb-6 rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="normalize"
            checked={normalize}
            onChange={(e) => {
              setNormalize(e.target.checked);
              try {
                localStorage.setItem('normalize', JSON.stringify(e.target.checked));
              } catch (e) {
                console.warn('Could not save normalize preference:', e);
              }
            }}
            className="h-5 w-5 rounded border-slate-500 bg-slate-800 text-primary-600 cursor-pointer"
          />
          <div className="flex-1">
            <label htmlFor="normalize" className="font-semibold cursor-pointer">
              Auto Normalize Volume
            </label>
            <p className="text-xs text-slate-400 mt-1">
              Prevents distortion and ensures consistent loudness
            </p>
          </div>
        </div>
      </div>
      <div className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-14 ${dragActive ? 'border-primary-400 bg-primary-500/10' : 'border-slate-700 bg-slate-900/50'}`} onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}>
        <div className="mx-auto mb-5 text-5xl text-primary-300">◉</div>
        <h2 className="text-xl font-bold">Drop an audio file here</h2>
        <p className="mt-2 text-sm text-slate-400">MP3, WAV, FLAC, OGG or M4A, up to 500 MB</p>
        <button type="button" disabled={loading} onClick={() => inputRef.current?.click()} className="mt-7 rounded-xl bg-primary-600 px-6 py-3 font-semibold shadow-lg shadow-primary-950/40 hover:bg-primary-500">Choose audio file</button>
        <input ref={inputRef} className="hidden" type="file" accept={ALLOWED_EXTENSIONS.join(',')} onChange={handleFileInput} />
      </div>
    </>
  );

  const renderLoadingState = () => (fileName || loading || taskId) && (
    <div className="mt-6 rounded-2xl bg-slate-900/70 p-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{fileName || 'Audio task'}</p><p className="mt-1 text-xs uppercase tracking-wider text-slate-500">{status}</p></div><div className="flex items-center gap-3"><span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-primary-300" /><span className="text-2xl font-bold text-primary-300">{progress}%</span></div></div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-500" style={{ width: `${progress}%` }} /></div>
    </div>
  );

  const renderSuccessState = () => status === 'SUCCESS' && (
    <div className="mt-6 animate-slide-in-right">
      <p className="mb-6 text-sm font-semibold text-emerald-300">Gata! Piesa a fost separată — mai jos poți asculta și descărca minusul (fără voce) și vocea izolată.</p>

      {/* Preview Player - Task 4.3 & 4.4 */}
      <div className="mb-6">
        <AudioPreviewPlayer
          taskId={taskId}
          apiBaseUrl={API_BASE_URL}
          isActive={activePreviewPlayer === taskId}
          onPlayStart={() => setActivePreviewPlayer(taskId)}
          onPlayStop={() => setActivePreviewPlayer(null)}
        />
      </div>

      {/* Speed Control - Task 5.4 */}
      <div className="mb-6">
        <SpeedControl
          taskId={taskId}
          originalDuration={audioDuration}
          onSpeedChange={(newSpeed) => {
            setSpeed(newSpeed);
            try {
              localStorage.setItem('speed', newSpeed.toString());
            } catch (e) {
              console.warn('Could not save speed preference:', e);
            }
          }}
          isProcessing={false}
        />
      </div>

      <div className="mb-6">
        <FormatSelector
          onFormatChange={(format, bitrate) => {
            setSelectedFormat(format);
            setSelectedBitrate(bitrate);
          }}
          inputFileSizeMb={fileSize}
          defaultFormat="wav"
          disabled={isExporting}
        />
      </div>

      {exportError && (
        <p role="alert" className="mb-6 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{exportError}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {[
          ['accompaniment', 'Minus (fără voce)', 'Instrumentalul piesei, fără voce — acesta e minusul.', results.accompanimentUrl, true],
          ['vocals', 'Voce izolată', 'Doar vocea, fără instrumental.', results.vocalsUrl, false],
        ].map(([type, label, description, source, primary]) => {
          const url = source?.startsWith('http') ? source : `${API_BASE_URL}${source || ''}`;
          const exportKey = `${type}-${selectedFormat}-${selectedBitrate || 'default'}`;
          const exportProgress = downloadProgress[exportKey];
          const isExportingThis = isExporting && exportProgress !== undefined;

          return (
            <div key={type} className={`rounded-2xl border p-4 ${primary ? 'border-primary-400/60 bg-primary-500/10' : 'border-slate-700 bg-slate-900/70'}`}>
              <p className="font-semibold">{label}</p>
              <p className="mt-1 mb-3 text-xs text-slate-400">{description}</p>
              <audio className="mb-4 w-full" controls src={url} />

              <button
                type="button"
                onClick={() => handleDownload(type)}
                disabled={isExporting}
                className={`w-full rounded-xl px-4 py-3 font-semibold transition-all ${
                  isExportingThis
                    ? 'bg-primary-600 cursor-not-allowed opacity-75'
                    : isExporting
                    ? 'cursor-not-allowed opacity-50 bg-slate-600'
                    : 'bg-primary-600 hover:bg-primary-500'
                }`}
              >
                {isExportingThis ? (
                  <div className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-white" />
                    <span>Converting to {selectedFormat.toUpperCase()}... {exportProgress}%</span>
                  </div>
                ) : (
                  `Descarcă ${label.toLowerCase()} (${selectedFormat.toUpperCase()})`
                )}
              </button>
            </div>
          );
        })}
      </div>
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
