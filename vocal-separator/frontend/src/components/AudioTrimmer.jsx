import React, { useState, useEffect } from 'react';

function AudioTrimmer({ file, onTrimChange, onUpload }) {
	const [duration, setDuration] = useState(0);
	const [trimStart, setTrimStart] = useState(0);
	const [trimEnd, setTrimEnd] = useState(0);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [showTrimmer, setShowTrimmer] = useState(false);

	useEffect(() => {
		if (!file) {
			setDuration(0);
			setTrimStart(0);
			setTrimEnd(0);
			return;
		}

		fetchAudioDuration(file);
	}, [file]);

	const fetchAudioDuration = async (audioFile) => {
		setLoading(true);
		setError('');

		try {
			const formData = new FormData();
			formData.append('file', audioFile);

			const response = await fetch('/api/audio-info', {
				method: 'POST',
				body: formData,
			});

			if (!response.ok) {
				throw new Error(`Failed to get audio info: ${response.statusText}`);
			}

			const data = await response.json();
			setDuration(data.duration);
			setTrimStart(0);
			setTrimEnd(data.duration);
		} catch (err) {
			setError(`Could not read audio duration: ${err.message}`);
			console.error('Audio info error:', err);
		} finally {
			setLoading(false);
		}
	};

	const handleTrimStartChange = (value) => {
		const val = parseFloat(value);
		if (val >= 0 && val < trimEnd) {
			setTrimStart(val);
			onTrimChange(val, trimEnd);
		}
	};

	const handleTrimEndChange = (value) => {
		const val = parseFloat(value);
		if (val > trimStart && val <= duration) {
			setTrimEnd(val);
			onTrimChange(trimStart, val);
		}
	};

	const resetTrim = () => {
		setTrimStart(0);
		setTrimEnd(duration);
		onTrimChange(null, null);
	};

	const formatTime = (seconds) => {
		if (!seconds || isNaN(seconds)) return '0:00';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	const trimDuration = trimEnd - trimStart;
	const trimPercentage = duration > 0 ? (trimDuration / duration) * 100 : 0;

	if (!file) return null;

	return (
		<div className="mt-6 rounded-2xl bg-slate-900/70 p-4 border border-slate-700">
			<button
				onClick={() => setShowTrimmer(!showTrimmer)}
				className="w-full text-left flex items-center justify-between font-semibold text-slate-200 hover:text-primary-300 transition-colors"
			>
				<span>✂️ Audio Trimmer (Optional)</span>
				<span className="text-sm text-slate-400">
					{showTrimmer ? '▼' : '▶'}
				</span>
			</button>

			{showTrimmer && (
				<div className="mt-4 space-y-4">
					{loading ? (
						<div className="text-center text-slate-400 py-4">
							<div className="animate-spin rounded-full h-6 w-6 border-2 border-primary-300 border-t-primary-600 mx-auto mb-2" />
							Reading audio duration...
						</div>
					) : error ? (
						<div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded p-3">
							{error}
						</div>
					) : duration > 0 ? (
						<>
							{/* Duration Info */}
							<div className="grid grid-cols-3 gap-3 text-sm">
								<div>
									<p className="text-slate-400">Total Duration</p>
									<p className="text-lg font-bold text-primary-300">
										{formatTime(duration)}
									</p>
								</div>
								<div>
									<p className="text-slate-400">Trim Duration</p>
									<p className="text-lg font-bold text-green-400">
										{formatTime(trimDuration)}
									</p>
								</div>
								<div>
									<p className="text-slate-400">Reduction</p>
									<p className="text-lg font-bold text-yellow-400">
										{(100 - trimPercentage).toFixed(0)}%
									</p>
								</div>
							</div>

							{/* Timeline Visualization */}
							<div className="bg-slate-800 rounded p-3">
								<div className="flex items-center justify-between mb-2">
									<span className="text-sm text-slate-400">
										{formatTime(trimStart)}
									</span>
									<span className="text-sm text-slate-400">
										{formatTime(trimEnd)}
									</span>
								</div>

								{/* Visual Timeline */}
								<div className="relative h-8 bg-slate-700 rounded overflow-hidden">
									{/* Trimmed area highlight */}
									<div
										className="absolute top-0 bottom-0 bg-primary-500/30 border-l-2 border-r-2 border-primary-400"
										style={{
											left: `${(trimStart / duration) * 100}%`,
											right: `${100 - (trimEnd / duration) * 100}%`,
										}}
									/>
									{/* Disabled area (before trim) */}
									<div
										className="absolute top-0 bottom-0 bg-slate-600/50"
										style={{
											width: `${(trimStart / duration) * 100}%`,
										}}
									/>
									{/* Disabled area (after trim) */}
									<div
										className="absolute top-0 bottom-0 bg-slate-600/50 right-0"
										style={{
											width: `${100 - (trimEnd / duration) * 100}%`,
										}}
									/>
								</div>
							</div>

							{/* Start Slider */}
							<div>
								<label className="text-sm text-slate-400 block mb-2">
									Start: {formatTime(trimStart)}
								</label>
								<input
									type="range"
									min="0"
									max={duration}
									step="0.1"
									value={trimStart}
									onChange={(e) => handleTrimStartChange(e.target.value)}
									className="w-full"
								/>
							</div>

							{/* End Slider */}
							<div>
								<label className="text-sm text-slate-400 block mb-2">
									End: {formatTime(trimEnd)}
								</label>
								<input
									type="range"
									min="0"
									max={duration}
									step="0.1"
									value={trimEnd}
									onChange={(e) => handleTrimEndChange(e.target.value)}
									className="w-full"
								/>
							</div>

							{/* Actions */}
							<div className="flex gap-2 flex-col sm:flex-row">
								<button
									onClick={resetTrim}
									className="flex-1 px-3 py-2 text-sm rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
								>
									Reset (Use Full Audio)
								</button>
								<button
									onClick={() => setShowTrimmer(false)}
									className="flex-1 px-3 py-2 text-sm rounded bg-slate-600 hover:bg-slate-500 text-slate-200 transition-colors font-semibold"
								>
									Cancel
								</button>
								{onUpload && (
									<button
										onClick={() => onUpload(trimStart, trimEnd)}
										className="flex-1 px-3 py-2 text-sm rounded bg-green-600 hover:bg-green-500 text-white transition-colors font-semibold"
									>
										✓ Upload & Separate
									</button>
								)}
							</div>

							{/* Info */}
							<p className="text-xs text-slate-400 text-center">
								💡 Trimming the audio before processing saves {(100 - trimPercentage).toFixed(0)}% processing time & resources
							</p>
						</>
					) : null}
				</div>
			)}
		</div>
	);
}

export default AudioTrimmer;
