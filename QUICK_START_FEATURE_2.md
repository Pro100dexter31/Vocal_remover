# Feature 2: Quick Start Guide - Export Multiple Formats

**Ready to test?** Follow these steps to see Feature 2 in action.

---

## 🚀 Quick Setup

### 1. Start the Backend (if not running)
```bash
# From vocal-separator directory
docker-compose up -d
# OR if running locally:
cd vocal-separator/backend
python -m uvicorn main:app --reload
```

### 2. Start the Frontend (if not running)
```bash
cd vocal-separator/frontend
npm start
```

Both services should now be running:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🧪 Testing the Feature

### Test 1: Simple Download (5 minutes)

1. **Upload Audio**
   - Open http://localhost:3000
   - Upload a 5-minute audio file (MP3, WAV, FLAC, OGG, or M4A)
   - Set separation intensity (optional, default is 50%)
   - Wait for processing to complete (Status: SUCCESS)

2. **Select Format**
   - Look for "Export Format" section
   - Click "MP3" button
   - Click "192k" bitrate button
   - Observe: File size estimate (~5.63 MB) and conversion time (~25s)

3. **Download**
   - Click "Download vocals (MP3)"
   - Watch the progress: "Converting to MP3... 0%"
   - Progress increases to 100%
   - File `vocals.mp3` downloads automatically

4. **Verify**
   - Open downloaded MP3 file in media player
   - Audio should play without issues
   - File size should be approximately 5.63 MB

### Test 2: Try All Formats (15 minutes)

After Test 1, test each format:

**2a. FLAC (Lossless)**
- Select "FLAC" format
- Observe: No bitrate options (lossless)
- File size estimate: ~30 MB
- Conversion time: ~8s
- Download and verify

**2b. OGG 128k (Low Quality)**
- Select "OGG" format
- Click "128k" bitrate
- File size estimate: ~3.75 MB
- Conversion time: ~18s
- Download and verify

**2c. WAV (Original Quality)**
- Select "WAV" format
- File size estimate: ~50 MB (original)
- Conversion time: <5s (pass-through)
- Download should complete very quickly

**2d. Multiple Downloads**
- While Format Selector is showing, download accompaniment as MP3 192k
- Then download vocals as FLAC
- Observe both downloads show independent progress

### Test 3: Error Handling (5 minutes)

**3a. Network Error Retry**
1. Open browser DevTools (Cmd+Shift+I or F12)
2. Go to "Network" tab
3. Click the throttling dropdown (usually says "No throttling")
4. Select "Offline"
5. Try to download a file
6. Wait 5 seconds
7. Observe "retrying... (1/2)" message
8. Set network back to "Online"
9. Download should automatically retry and complete

**3b. localStorage Persistence**
1. Download audio with MP3 320k selected
2. Refresh the page (Cmd+R)
3. After processing completes again, check FormatSelector
4. MP3 320k should still be selected
5. localStorage is working! ✅

---

## 📊 Quick Metrics

### File Size Estimates
```
Input: 50 MB WAV file (5 minutes)

Format        Estimated Size   Color     Speed
──────────────────────────────────────────────
MP3 128k      3.75 MB         🟡 Low    2.5x slower
MP3 192k      5.63 MB         🟡 Med    2x slower
MP3 320k      9.38 MB         🟡 High   1.4x slower
FLAC          30 MB           🟢 Lossless 3x faster
OGG 128k      3.75 MB         🟡 Low    2x slower
OGG 192k      5.63 MB         🟡 Med    2x slower
WAV           50 MB           🟢 Original Instant
```

### Expected Conversion Times
```
MP3 192k (50 MB):  20-30 seconds  (0.4s per MB)
FLAC (50 MB):      5-15 seconds   (0.15s per MB)
OGG 192k (50 MB):  15-25 seconds  (0.35s per MB)
WAV (50 MB):       <5 seconds     (pass-through)
```

---

## 🎯 What to Look For

### Visual Elements ✅
- [ ] Format buttons highlight when selected
- [ ] Bitrate options appear ONLY for MP3 and OGG
- [ ] File size estimate updates when format changes
- [ ] Conversion time estimate shows in seconds or minutes
- [ ] "%" of original shows accurate compression ratio

### Functionality ✅
- [ ] Download button shows spinner during conversion
- [ ] Progress percentage displays (0-100%)
- [ ] Format name shows in progress text ("Converting to MP3...")
- [ ] File downloads with correct name (vocals.mp3, etc.)
- [ ] Progress clears after 2 seconds

### Error Handling ✅
- [ ] Network errors show "retrying..." message
- [ ] Automatic retry works (up to 2 times)
- [ ] Error messages are clear and helpful
- [ ] Can retry manually if all retries fail

### Performance ✅
- [ ] MP3 conversions complete within 45 seconds (50MB)
- [ ] FLAC conversions complete within 15 seconds (50MB)
- [ ] OGG conversions complete within 30 seconds (50MB)
- [ ] WAV download instant (< 5 seconds)

---

## 🐛 Troubleshooting

**Q: "Converting..." spinner won't stop**
- A: Check backend logs. Might be processing large file. Wait longer.

**Q: Downloaded file won't play**
- A: Check file format. Try opening in different player (VLC, Audacity).

**Q: Format buttons not appearing**
- A: Ensure audio processing completed (Status: SUCCESS).

**Q: localStorage preferences not saving**
- A: Check browser storage is enabled. Try incognito mode. Check console for errors.

**Q: Backend not responding**
- A: Check `http://localhost:8000/api/health`. Backend may not be running.

**Q: File sizes much larger/smaller than expected**
- A: Check selected bitrate. Try different format. Check input file size.

---

## 📝 Test Checklist

Use this to verify Feature 2 is working correctly:

### Setup
- [ ] Backend running (health check passes)
- [ ] Frontend running (localhost:3000 loads)
- [ ] Both can communicate (no CORS errors in console)

### Feature 2.4: Format Selector
- [ ] Format buttons visible (MP3, FLAC, OGG, WAV)
- [ ] Buttons highlight when selected
- [ ] Bitrate options appear for MP3 and OGG only
- [ ] File size estimates display
- [ ] Conversion time estimates display

### Feature 2.5: Download Logic
- [ ] Download buttons functional
- [ ] Progress spinner appears during conversion
- [ ] Progress percentage updates in real-time
- [ ] Conversion format name shows in progress ("Converting to MP3...")
- [ ] File downloads automatically
- [ ] Multiple formats can be downloaded

### Feature 2.6: Error Handling & Performance
- [ ] Network errors trigger retry (offline mode test)
- [ ] Files download successfully after retry
- [ ] Conversion times within acceptable range
- [ ] File sizes match estimates (±10%)
- [ ] Downloaded files play without corruption

### localStorage Persistence
- [ ] Format preference saved after first download
- [ ] Format restored after page refresh
- [ ] Bitrate preference also saved/restored

---

## 🎬 Demo Scenario (20 minutes)

**Perfect for showing Feature 2 to stakeholders:**

1. **Show Upload** (1 min)
   - Upload sample audio file
   - Show separation intensity slider (Feature 1)
   - Wait for "Processing..." to complete

2. **Show Format Options** (3 min)
   - Highlight all 4 format buttons
   - Click MP3 to show bitrate options
   - Click FLAC to show no bitrate needed
   - Show file size estimates and conversion times

3. **Download MP3** (2 min)
   - Select MP3 192k
   - Click download
   - Show progress with spinner and percentage
   - Download completes
   - Open downloaded file to verify

4. **Download Lossless** (2 min)
   - Select FLAC
   - Note: no bitrate selection
   - Download
   - Show very fast completion (lossless, faster conversion)

5. **Download Low Bandwidth** (2 min)
   - Select OGG 128k
   - Show file size is half of 192k version
   - Download and verify

6. **Show Error Recovery** (3 min)
   - Try to download with network offline
   - Show "retrying..." message
   - Come back online
   - Show successful retry
   - Explain automatic retry happens up to 2 times

7. **Show Persistence** (2 min)
   - Download another file with MP3 320k selected
   - Refresh page
   - After processing, show MP3 320k still selected
   - Explain localStorage saves user preference

8. **Summary** (2 min)
   - 7 format combinations (MP3×3, FLAC, OGG×2, WAV)
   - One-click download with progress tracking
   - Automatic error recovery
   - Optimized file sizes
   - Smart format selection

---

## 🔗 Key Files to Review

If you want to dive deeper into the implementation:

### Backend
- `vocal-separator/backend/audio_converter.py` - All conversion logic
- `vocal-separator/backend/main.py` (lines 190-286) - /api/export endpoint
- `vocal-separator/backend/test_audio_conversions.py` - Test suite

### Frontend
- `vocal-separator/frontend/src/components/FormatSelector.jsx` - Format UI
- `vocal-separator/frontend/src/App.jsx` (handleDownload function) - Download logic

### Documentation
- `FEATURE_2_COMPLETE_IMPLEMENTATION.md` - Full implementation details
- `frontend_integration_tests.md` - Detailed test procedures
- `FEATURE_2_TASK_2_4_2_5_2_6_SUMMARY.md` - Task-specific summary

---

## 🎉 Success Criteria

Feature 2 is working correctly when:

✅ All 7 format combinations download successfully
✅ Downloaded files play without corruption
✅ File sizes match estimates within ±10%
✅ Conversion times are within 45 seconds for lossy formats
✅ Progress display updates smoothly (0-100%)
✅ Error recovery with retry works automatically
✅ localStorage persists format preference
✅ Multiple downloads don't interfere with each other
✅ UI remains responsive during conversion
✅ No browser console errors

---

## 📞 Need Help?

### Check Logs
```bash
# Backend logs
docker logs vocal-separator-backend
# OR
tail -f backend.log

# Frontend logs
# Open browser DevTools → Console tab
```

### Verify Endpoints
```bash
# Health check
curl http://localhost:8000/api/health

# Try export API directly
curl -X POST "http://localhost:8000/api/export/test-task-id?file_type=vocals&output_format=mp3&bitrate=192k"
```

### Review Files
- Backend: Check `audio_converter.py` for conversion logic
- Frontend: Check `FormatSelector.jsx` for UI logic
- Tests: Run `python test_audio_conversions.py` for backend tests

---

**Happy Testing! 🎵**

For complete testing procedures, see `frontend_integration_tests.md`

