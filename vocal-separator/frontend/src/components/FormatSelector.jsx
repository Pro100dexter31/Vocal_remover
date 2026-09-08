import { useState, useEffect } from 'react';

const FORMAT_CONFIG = {
  mp3: {
    label: 'MP3 (Lossy)',
    icon: '🎵',
    bitrates: ['128k', '192k', '320k'],
    defaultBitrate: '192k',
    description: 'High compression, smaller files',
  },
  flac: {
    label: 'FLAC (Lossless)',
    icon: '🔊',
    bitrates: null,
    description: 'Perfect quality, moderate file size',
  },
  ogg: {
    label: 'OGG (Lossy)',
    icon: '🎧',
    bitrates: ['128k', '192k'],
    defaultBitrate: '192k',
    description: 'Alternative to MP3, good compression',
  },
  wav: {
    label: 'WAV (Lossless)',
    icon: '💿',
    bitrates: null,
    description: 'Original quality, large files',
  },
};

const BITRATE_QUALITY = {
  '128k': 'Low Quality',
  '192k': 'Standard Quality',
  '320k': 'High Quality',
};

function estimateFileSize(inputSizeMb, format, bitrate = null) {
  const ratios = {
    mp3: { '128k': 0.075, '192k': 0.113, '320k': 0.188 },
    flac: 0.6,
    ogg: { '128k': 0.075, '192k': 0.113 },
    wav: 1.0,
  };

  if (format === 'mp3' || format === 'ogg') {
    const ratio = ratios[format]?.[bitrate] || 0.113;
    return inputSizeMb * ratio;
  }

  const ratio = ratios[format] || 1.0;
  return inputSizeMb * ratio;
}

function estimateConversionTime(fileSizeMb, format) {
  // Rough estimates in seconds based on format and file size
  const timePerMb = {
    mp3: 0.4,    // ~2.5 min per 5-min song (50MB)
    flac: 0.15,  // ~1 min per 5-min song
    ogg: 0.35,   // ~2 min per 5-min song
    wav: 0.01,   // ~1 sec per 5-min song (pass-through)
  };

  const seconds = fileSizeMb * (timePerMb[format] || 0.3);

  if (seconds < 60) {
    return `${Math.ceil(seconds)}s`;
  }
  const minutes = Math.ceil(seconds / 60);
  return `${minutes}m`;
}

function FormatSelector({
  onFormatChange,
  inputFileSizeMb = 0,
  defaultFormat = 'wav',
  disabled = false
}) {
  const [selectedFormat, setSelectedFormat] = useState(defaultFormat);
  const [selectedBitrate, setSelectedBitrate] = useState(
    FORMAT_CONFIG[defaultFormat]?.defaultBitrate || null
  );

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('preferredAudioFormat');
      if (saved) {
        const { format, bitrate } = JSON.parse(saved);
        setSelectedFormat(format);
        setSelectedBitrate(bitrate || FORMAT_CONFIG[format]?.defaultBitrate || null);
      }
    } catch (e) {
      console.warn('Could not load saved format preference:', e);
    }
  }, []);

  // Save to localStorage and notify parent
  const handleFormatChange = (format) => {
    setSelectedFormat(format);
    const bitrate = FORMAT_CONFIG[format]?.defaultBitrate || null;
    setSelectedBitrate(bitrate);

    try {
      localStorage.setItem('preferredAudioFormat', JSON.stringify({ format, bitrate }));
    } catch (e) {
      console.warn('Could not save format preference:', e);
    }

    if (onFormatChange) {
      onFormatChange(format, bitrate);
    }
  };

  const handleBitrateChange = (bitrate) => {
    setSelectedBitrate(bitrate);

    try {
      localStorage.setItem('preferredAudioFormat', JSON.stringify({ format: selectedFormat, bitrate }));
    } catch (e) {
      console.warn('Could not save format preference:', e);
    }

    if (onFormatChange) {
      onFormatChange(selectedFormat, bitrate);
    }
  };

  const config = FORMAT_CONFIG[selectedFormat];
  const estimatedSize = estimateFileSize(inputFileSizeMb, selectedFormat, selectedBitrate);
  const estimatedTime = estimateConversionTime(inputFileSizeMb, selectedFormat);

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
      <h3 className="mb-4 text-lg font-semibold">Export Format</h3>

      {/* Format Selection Buttons */}
      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {Object.entries(FORMAT_CONFIG).map(([format, cfg]) => (
          <button
            key={format}
            onClick={() => handleFormatChange(format)}
            disabled={disabled}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
              selectedFormat === format
                ? 'border-primary-400 bg-primary-500/20 text-primary-200 ring-2 ring-primary-500/50'
                : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:bg-slate-700'
            } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
            title={cfg.description}
          >
            <span className="mr-1">{cfg.icon}</span>
            {format.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Format Description */}
      <p className="mb-4 text-sm text-slate-400">{config.description}</p>

      {/* Bitrate Selection (for lossy formats) */}
      {config.bitrates && (
        <div className="mb-6">
          <p className="mb-2 text-sm font-semibold text-slate-300">Quality</p>
          <div className="flex flex-wrap gap-2">
            {config.bitrates.map((bitrate) => (
              <button
                key={bitrate}
                onClick={() => handleBitrateChange(bitrate)}
                disabled={disabled}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                  selectedBitrate === bitrate
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                title={BITRATE_QUALITY[bitrate] || bitrate}
              >
                {bitrate}
                <span className="ml-1 text-xs opacity-75">({BITRATE_QUALITY[bitrate]})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* File Size and Time Estimates */}
      {inputFileSizeMb > 0 && (
        <div className="rounded-lg border border-slate-600 bg-slate-800/50 p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Est. File Size
              </p>
              <p className="mt-1 text-lg font-bold text-slate-200">
                {estimatedSize.toFixed(2)} MB
              </p>
              <p className="mt-1 text-xs text-slate-500">
                ~{((estimatedSize / inputFileSizeMb) * 100).toFixed(0)}% of original
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Est. Time
              </p>
              <p className="mt-1 text-lg font-bold text-slate-200">{estimatedTime}</p>
              <p className="mt-1 text-xs text-slate-500">conversion time</p>
            </div>
          </div>
        </div>
      )}

      {/* Information Tooltip */}
      <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/50 p-3">
        <p className="text-xs text-slate-400">
          <span className="font-semibold">💡 Tip:</span> Lossy formats (MP3, OGG) offer better compression.
          Lossless formats (WAV, FLAC) preserve original quality.
        </p>
      </div>
    </div>
  );
}

export default FormatSelector;
