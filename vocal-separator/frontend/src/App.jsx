import { useEffect, useRef, useState } from 'react';
import FormatSelector from './components/FormatSelector';
import AudioPreviewPlayer from './components/AudioPreviewPlayer';
import SpeedControl from './components/SpeedControl';
import PitchControl from './components/PitchControl';
import VolumeMeter from './components/VolumeMeter';
import WaveformComparison from './components/WaveformComparison';
import AudioTrimmer from './components/AudioTrimmer';

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
  const [normalizationMethod, setNormalizationMethod] = useState('peak');
  const [speed, setSpeed] = useState(1.0);  // Task 5.4: Speed control
  const [activePreviewPlayer, setActivePreviewPlayer] = useState(null);  // Task 4.4: Track active player
  const [audioDuration, setAudioDuration] = useState(0);  // Track original duration
  const [speedJob, setSpeedJob] = useState({ speed: 1.0, status: 'ready', jobId: null, message: '' });
  const [normalizationInfo, setNormalizationInfo] = useState(null);  // Task 3.5: Volume meter data
  const [seekRequest, setSeekRequest] = useState(null);  // Task 6.3: click waveform to seek preview
  const [previewCurrentTime, setPreviewCurrentTime] = useState(0);  // live playhead for waveform
  const [sourceMode, setSourceMode] = useState('file');  // Task 7.6: 'file' | 'youtube'
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [youtubeSubmitting, setYoutubeSubmitting] = useState(false);
  const [youtubeError, setYoutubeError] = useState('');
  const [stage, setStage] = useState(null);  // Task 7.7: 'downloading' | 'separating' | null
  const [trimStartSeconds, setTrimStartSeconds] = useState(null);  // Audio trimmer: start time
  const [trimEndSeconds, setTrimEndSeconds] = useState(null);  // Audio trimmer: end time
  const [selectedFile, setSelectedFile] = useState(null);  // Store file for trimmer
  const speedPollRef = useRef(null);
  const inputRef = useRef(null);
  const pollingRef = useRef(null);
  const abortControllerRef = useRef(new AbortController());

  // Load settings from localStorage on mount (Task 5.6)
  useEffect(() => {
    try {
      const savedSeparationLevel = localStorage.getItem('separationLevel');
      if (savedSeparationLevel) setSeparationLevel(parseInt(savedSeparationLevel));

      const savedNormalize = localStorage.getItem('normalize');
      if (savedNormalize) setNormalize(JSON.parse(savedNormalize));

      const savedNormalizationMethod = localStorage.getItem('normalizationMethod');
      if (savedNormalizationMethod === 'peak' || savedNormalizationMethod === 'lufs') {
        setNormalizationMethod(savedNormalizationMethod);
      }

      const savedSpeed = localStorage.getItem('speed');
      if (savedSpeed) setSpeed(parseFloat(savedSpeed));
    } catch (e) {
      console.warn('Could not load settings from localStorage:', e);
    }
  }, []);

  const checkStatus = async (currentTaskId) => {
    const response = await fetch(`${API_BASE_URL}/api/status/${currentTaskId}`);
    if (!response.ok) throw new Error('Could not read processing status.');
    const data = await response.json();
    setStatus(data.status);
    setProgress(data.progress || 0);
    setStage(data.stage || null);
    if (data.status === 'SUCCESS') {
      setResults({ vocalsUrl: data.vocals_url, accompanimentUrl: data.accompaniment_url });
      setNormalizationInfo(data.normalization || null);
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

  const requestSpeedVariant = async (targetSpeed) => {
    window.clearTimeout(speedPollRef.current);

    if (targetSpeed === 1.0) {
      setSpeedJob({ speed: 1.0, status: 'ready', jobId: null, message: '' });
      return;
    }

    setSpeedJob({ speed: targetSpeed, status: 'processing', jobId: null, message: 'Requesting speed adjustment...' });

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/process/${taskId}?speed=${targetSpeed}`,
        { method: 'POST' }
      );
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        setSpeedJob({ speed: targetSpeed, status: 'error', jobId: null, message: data.detail || 'Speed adjustment failed to start.' });
        return;
      }

      if (data.status === 'completed') {
        setSpeedJob({ speed: targetSpeed, status: 'ready', jobId: null, message: '' });
        return;
      }

      const jobId = data.task_id;
      setSpeedJob({ speed: targetSpeed, status: 'processing', jobId, message: 'Processing speed adjustment...' });

      const poll = async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
          const statusData = await statusResponse.json();

          if (statusData.status === 'SUCCESS') {
            setSpeedJob({ speed: targetSpeed, status: 'ready', jobId, message: '' });
            return;
          }
          if (statusData.status === 'FAILURE') {
            setSpeedJob({ speed: targetSpeed, status: 'error', jobId, message: statusData.error || 'Speed adjustment failed.' });
            return;
          }
          speedPollRef.current = window.setTimeout(poll, POLLING_INTERVAL);
        } catch (pollError) {
          setSpeedJob({ speed: targetSpeed, status: 'error', jobId, message: pollError.message || 'Could not check speed adjustment status.' });
        }
      };
      poll();
    } catch (err) {
      setSpeedJob({ speed: targetSpeed, status: 'error', jobId: null, message: err.message || 'Speed adjustment failed to start.' });
    }
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
    return () => {
      window.clearTimeout(pollingRef.current);
      window.clearTimeout(speedPollRef.current);
    };
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
    formData.append('normalization_method', normalizationMethod);
    formData.append('speed', speed.toString());
    // Add optional trim parameters
    if (trimStartSeconds !== null) formData.append('trim_start_seconds', trimStartSeconds.toString());
    if (trimEndSeconds !== null) formData.append('trim_end_seconds', trimEndSeconds.toString());

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

  const isLikelyYoutubeUrl = (url) =>
    /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)/.test(url.trim());

  const submitYoutubeUrl = async () => {
    const trimmed = youtubeUrl.trim();
    if (!isLikelyYoutubeUrl(trimmed)) {
      setYoutubeError('Nu pare a fi un link YouTube valid (youtube.com/watch, youtu.be, sau /shorts/).');
      return;
    }

    setYoutubeSubmitting(true);
    setYoutubeError('');
    setError('');
    setResults({ vocalsUrl: '', accompanimentUrl: '' });
    setStatus('UPLOADING');
    setStage('downloading');
    setProgress(0);

    try {
      const response = await fetch(`${API_BASE_URL}/api/youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: trimmed,
          separation_intensity: separationLevel / 100,
          normalize,
          normalization_method: normalizationMethod,
          speed,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `Extraction failed (${response.status})`);
      }

      setFileName(trimmed);
      setTaskId(data.task_id);
      setStatus(data.status || 'PENDING');
      startPolling(data.task_id);
    } catch (err) {
      setYoutubeError(err.message || 'Could not start extraction from YouTube.');
      setStatus('FAILED');
    } finally {
      setYoutubeSubmitting(false);
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
    setFileSize(file.size / (1024 * 1024));
    setProgress(0);
    setSelectedFile(file);  // Store for trimmer
    // Don't upload yet - wait for trimmer interaction
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
    const usingSpeedVariant = speed !== 1.0;
    const key = `${fileType}-${selectedFormat}-${selectedBitrate || 'default'}`;

    if (usingSpeedVariant && speedJob.status !== 'ready') {
      setExportError(
        speedJob.status === 'error'
          ? speedJob.message || 'Speed adjustment failed.'
          : 'Wait for the speed adjustment to finish before downloading.'
      );
      return;
    }

    try {
      setIsExporting(true);
      setExportError('');

      abortControllerRef.current = new AbortController();

      const progressTracker = getConversionProgress(selectedFormat, fileSize);
      const progressInterval = setInterval(() => {
        const pct = progressTracker.getProgress();
        setDownloadProgress((prev) => ({ ...prev, [key]: pct }));
      }, 500);

      // Speed-adjusted variants are served pre-encoded (master's format) by
      // /api/download; only the 1.0x master supports on-demand format conversion.
      const response = usingSpeedVariant
        ? await fetch(
            `${API_BASE_URL}/api/download/${taskId}/${fileType}?speed=${speed}`,
            { signal: abortControllerRef.current.signal }
          )
        : await (async () => {
            const params = new URLSearchParams({
              file_type: fileType,
              output_format: selectedFormat,
            });
            if (selectedBitrate && (selectedFormat === 'mp3' || selectedFormat === 'ogg')) {
              params.append('bitrate', selectedBitrate);
            }
            return fetch(`${API_BASE_URL}/api/export/${taskId}?${params}`, {
              method: 'POST',
              signal: abortControllerRef.current.signal,
            });
          })();

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
    setActivePreviewPlayer(null);
    setAudioDuration(0);
    setSpeedJob({ speed: 1.0, status: 'ready', jobId: null, message: '' });
    setNormalizationInfo(null);
    setSeekRequest(null);
    setYoutubeUrl('');
    setYoutubeError('');
    setStage(null);
    setPreviewCurrentTime(0);
  };

  const renderUploadZone = () => (
    <>
      <div className="mb-6 flex gap-2 rounded-xl bg-slate-900/70 p-1.5">
        {[
          { value: 'file', label: '📁 Încarcă fișier' },
          { value: 'youtube', label: '📺 Link YouTube' },
        ].map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => {
              setSourceMode(tab.value);
              setError('');
              setYoutubeError('');
            }}
            className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all ${
              sourceMode === tab.value
                ? 'bg-primary-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
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

        {normalize && (
          <div className="mt-4 flex items-center gap-2 border-t border-slate-700 pt-4">
            <span className="text-xs font-semibold text-slate-400">Target:</span>
            {[
              { value: 'peak', label: '-1 dB Peak', title: 'Classic peak normalization — safe headroom, no clipping' },
              { value: 'lufs', label: '-14 LUFS', title: 'Perceived loudness target used by YouTube/Spotify' },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                title={option.title}
                onClick={() => {
                  setNormalizationMethod(option.value);
                  try {
                    localStorage.setItem('normalizationMethod', option.value);
                  } catch (e) {
                    console.warn('Could not save normalization method:', e);
                  }
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  normalizationMethod === option.value
                    ? 'border-primary-400 bg-primary-500/20 text-primary-200 ring-2 ring-primary-500/50'
                    : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {sourceMode === 'file' ? (
        <div className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-14 ${dragActive ? 'border-primary-400 bg-primary-500/10' : 'border-slate-700 bg-slate-900/50'}`} onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}>
          <div className="mx-auto mb-5 text-5xl text-primary-300">◉</div>
          <h2 className="text-xl font-bold">Drop an audio file here</h2>
          <p className="mt-2 text-sm text-slate-400">MP3, WAV, FLAC, OGG or M4A, up to 500 MB</p>
          <button type="button" disabled={loading} onClick={() => inputRef.current?.click()} className="mt-7 rounded-xl bg-primary-600 px-6 py-3 font-semibold shadow-lg shadow-primary-950/40 hover:bg-primary-500">Choose audio file</button>
          <input ref={inputRef} className="hidden" type="file" accept={ALLOWED_EXTENSIONS.join(',')} onChange={handleFileInput} />
        </div>
      ) : (
        <div className="rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/50 p-8 sm:p-10">
          <div className="mx-auto mb-4 text-center text-5xl text-primary-300">📺</div>
          <h2 className="text-center text-xl font-bold">Lipește un link YouTube</h2>
          <p className="mt-2 text-center text-sm text-slate-400">Video de maxim 15 minute · extras la 320kbps</p>

          <div className="mx-auto mt-6 max-w-lg">
            <div className="flex gap-2">
              <input
                type="text"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !youtubeSubmitting && submitYoutubeUrl()}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={youtubeSubmitting || loading}
                className="flex-1 rounded-xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:border-primary-400 focus:outline-none"
              />
              <button
                type="button"
                onClick={submitYoutubeUrl}
                disabled={youtubeSubmitting || loading || !youtubeUrl.trim()}
                className="rounded-xl bg-primary-600 px-6 py-3 font-semibold shadow-lg shadow-primary-950/40 hover:bg-primary-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {youtubeSubmitting ? 'Se verifică...' : 'Extrage'}
              </button>
            </div>

            {youtubeError && (
              <p role="alert" className="mt-3 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{youtubeError}</p>
            )}

            <p className="mt-4 text-xs text-slate-500">
              ⚠️ Folosește doar cu conținut pentru care ai drepturi (piesele tale, conținut liber de drepturi, sau uz personal permis). Descărcarea de pe YouTube poate încălca Termenii de Serviciu ai platformei pentru conținut protejat prin drepturi de autor.
            </p>
          </div>
        </div>
      )}
    </>
  );

  const stageLabel = stage === 'downloading'
    ? '1. Descarc audio de pe YouTube...'
    : stage === 'separating'
      ? '2. Separ vocea...'
      : status;

  const renderLoadingState = () => (fileName || loading || taskId) && (
    <div className="mt-6 rounded-2xl bg-slate-900/70 p-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{fileName || 'Audio task'}</p><p className="mt-1 text-xs uppercase tracking-wider text-slate-500">{stageLabel}</p></div><div className="flex items-center gap-3"><span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-primary-300" /><span className="text-2xl font-bold text-primary-300">{progress}%</span></div></div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-500" style={{ width: `${progress}%` }} /></div>
    </div>
  );

  const renderSuccessState = () => status === 'SUCCESS' && (
    <div className="mt-6 animate-slide-in-right">
      <p className="mb-6 text-sm font-semibold text-emerald-300">Gata! Piesa a fost separată — mai jos poți asculta și descărca minusul (fără voce) și vocea izolată.</p>

      {/* Preview Player - Task 4.3 & 4.4 & 5.5 */}
      <div className="mb-6">
        <AudioPreviewPlayer
          taskId={taskId}
          apiBaseUrl={API_BASE_URL}
          isActive={activePreviewPlayer === taskId}
          onPlayStart={() => setActivePreviewPlayer(taskId)}
          onPlayStop={() => setActivePreviewPlayer(null)}
          previewSpeed={speed}
          onDurationChange={setAudioDuration}
          seekTo={seekRequest}
          onTimeUpdate={setPreviewCurrentTime}
        />
      </div>

      {/* Volume Meter - Task 3.5 */}
      {normalizationInfo && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          <VolumeMeter
            title={`Voce izolată — ${normalizationInfo.method === 'lufs' ? 'LUFS' : 'Peak dB'}`}
            beforeDb={normalizationInfo.vocals?.before_db}
            afterDb={normalizationInfo.vocals?.after_db}
          />
          <VolumeMeter
            title={`Minus — ${normalizationInfo.method === 'lufs' ? 'LUFS' : 'Peak dB'}`}
            beforeDb={normalizationInfo.accompaniment?.before_db}
            afterDb={normalizationInfo.accompaniment?.after_db}
          />
        </div>
      )}

      {/* Speed Control - Task 5.4 */}
      <div className="mb-6">
        <SpeedControl
          taskId={taskId}
          originalDuration={audioDuration}
          value={speed}
          onSpeedChange={(newSpeed) => {
            setSpeed(newSpeed);
            try {
              localStorage.setItem('speed', newSpeed.toString());
            } catch (e) {
              console.warn('Could not save speed preference:', e);
            }
            requestSpeedVariant(newSpeed);
          }}
          isProcessing={speedJob.status === 'processing'}
          statusMessage={speedJob.status !== 'ready' ? speedJob.message : ''}
        />
      </div>

      {/* Pitch Control - schimbare tonalitate, doar minus */}
      <div className="mb-6">
        <PitchControl taskId={taskId} apiBaseUrl={API_BASE_URL} />
      </div>

      {/* Waveform Comparison - Feature 6 */}
      <div className="mb-6">
        <WaveformComparison
          taskId={taskId}
          apiBaseUrl={API_BASE_URL}
          duration={audioDuration}
          currentTime={previewCurrentTime}
          onSeek={(time) => setSeekRequest({ time, requestId: Date.now() })}
        />
      </div>

      <div className="mb-6">
        {speed !== 1.0 && (
          <p className="mb-2 text-xs text-yellow-300">
            Format/bitrate choice below only applies at 1.0x — the {speed}x download uses the separated track's original format.
          </p>
        )}
        <FormatSelector
          onFormatChange={(format, bitrate) => {
            setSelectedFormat(format);
            setSelectedBitrate(bitrate);
          }}
          inputFileSizeMb={fileSize}
          defaultFormat="wav"
          disabled={isExporting || speed !== 1.0}
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
          const usingSpeedVariant = speed !== 1.0;
          const speedNotReady = usingSpeedVariant && speedJob.status !== 'ready';

          return (
            <div key={type} className={`rounded-2xl border p-4 ${primary ? 'border-primary-400/60 bg-primary-500/10' : 'border-slate-700 bg-slate-900/70'}`}>
              <p className="font-semibold">{label}</p>
              <p className="mt-1 mb-3 text-xs text-slate-400">{description}</p>
              <audio className="mb-4 w-full" controls src={url} />

              <button
                type="button"
                onClick={() => handleDownload(type)}
                disabled={isExporting || speedNotReady}
                className={`w-full rounded-xl px-4 py-3 font-semibold transition-all ${
                  isExportingThis
                    ? 'bg-primary-600 cursor-not-allowed opacity-75'
                    : isExporting || speedNotReady
                    ? 'cursor-not-allowed opacity-50 bg-slate-600'
                    : 'bg-primary-600 hover:bg-primary-500'
                }`}
              >
                {isExportingThis ? (
                  <div className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-white" />
                    <span>Converting to {selectedFormat.toUpperCase()}... {exportProgress}%</span>
                  </div>
                ) : usingSpeedVariant && speedJob.status === 'processing' ? (
                  <div className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-white" />
                    <span>Preparing {speed}x version...</span>
                  </div>
                ) : usingSpeedVariant ? (
                  `Descarcă ${label.toLowerCase()} (${speed}x)`
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
      <section className="glass-effect animate-slide-in-left rounded-3xl p-5 sm:p-8">{renderUploadZone()}{selectedFile && <AudioTrimmer file={selectedFile} onTrimChange={(start, end) => { setTrimStartSeconds(start); setTrimEndSeconds(end); }} onUpload={(start, end) => { setTrimStartSeconds(start); setTrimEndSeconds(end); uploadFile(selectedFile); }} />}{error && <p role="alert" className="mt-5 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}{renderLoadingState()}{renderSuccessState()}{(status === 'SUCCESS' || status === 'FAILED') && <button type="button" onClick={handleReset} className="mt-5 text-sm font-semibold text-slate-400 underline-offset-4 hover:text-white hover:underline">Process another file</button>}</section>
      <footer className="mt-8 text-center text-sm text-slate-500">Vocal Separator · Audio processing powered by Demucs</footer>
    </div></main>
  );
}

export default App;
