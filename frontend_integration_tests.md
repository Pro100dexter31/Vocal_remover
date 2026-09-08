# Frontend Integration Tests - Task 2.5 & 2.6

## Manual Testing Guide

### Prerequisites

1. Backend running on `http://localhost:8000`
2. Frontend running on `http://localhost:3000` (or configured API URL)
3. Test audio file (5-30 minutes) already processed and ready for export

---

## Test Suite 1: FormatSelector Component

### Test 1.1: Format Selection

**Steps**:
1. After audio processing completes, observe the "Export Format" section
2. Click each format button (MP3, FLAC, OGG, WAV)
3. Verify the button highlights with primary color when selected

**Expected Results**:
- ✅ Format buttons are clickable
- ✅ Only one format is selected at a time
- ✅ Selection persists when switching between buttons
- ✅ Descriptions update for each format

---

### Test 1.2: Bitrate Selection (Lossy Formats)

**Steps**:
1. Select "MP3" format
2. Verify "Quality" options appear with 128k, 192k, 320k
3. Click each bitrate button
4. Switch to "FLAC" format
5. Verify "Quality" section disappears

**Expected Results**:
- ✅ Bitrate buttons appear ONLY for MP3 and OGG
- ✅ FLAC and WAV don't show bitrate options
- ✅ Each bitrate has quality label (Low/Standard/High)
- ✅ Switching away from lossy formats removes bitrate UI

---

### Test 1.3: File Size Estimation

**Steps**:
1. Select a format (e.g., MP3 192k)
2. Observe "Est. File Size" box
3. Switch between different formats
4. Note how file size estimates change

**Expected Results**:
- ✅ File size displays in MB (e.g., "5.63 MB")
- ✅ Shows percentage of original file
- ✅ Updates immediately when format changes
- ✅ MP3 128k < MP3 192k < MP3 320k
- ✅ MP3 192k ≈ OGG 192k < FLAC < WAV (original)

**Example for 50 MB file**:
```
MP3 128k:  3.75 MB (7.5% of original)
MP3 192k:  5.63 MB (11.3% of original)
MP3 320k:  9.38 MB (18.8% of original)
FLAC:     30.00 MB (60% of original)
OGG 128k:  3.75 MB (7.5% of original)
OGG 192k:  5.63 MB (11.3% of original)
WAV:      50.00 MB (100% of original)
```

---

### Test 1.4: Conversion Time Estimation

**Steps**:
1. Select different formats
2. Observe "Est. Time" in the same box
3. Compare across formats for same file

**Expected Results**:
- ✅ Time shows in human-readable format (e.g., "20s", "2m")
- ✅ Updates when format changes
- ✅ MP3/OGG take longer than FLAC
- ✅ WAV is nearly instant
- ✅ Estimates are reasonable (5 min file shouldn't take 1+ minute to convert to FLAC)

**Example for 50 MB (5-minute) file**:
```
MP3 192k: ~20s (20-30 second range)
FLAC:     ~8s  (5-10 second range)
OGG 192k: ~18s (15-25 second range)
WAV:      ~1s  (nearly instant)
```

---

### Test 1.5: localStorage Persistence

**Steps**:
1. Select MP3 format with 320k bitrate
2. Click download for vocals
3. Wait for download to complete
4. Refresh the browser page (Cmd+R)
5. After processing completes again, observe FormatSelector
6. Download format should still be MP3 with 320k selected

**Expected Results**:
- ✅ Format preference is saved to localStorage
- ✅ Format is restored after page refresh
- ✅ Bitrate selection is also restored
- ✅ Users don't need to re-select format

---

## Test Suite 2: Download Logic & Progress

### Test 2.1: MP3 Download (192k)

**Steps**:
1. Select "MP3" format with "192k" bitrate
2. Click "Download vocals" button
3. Watch for progress display
4. Wait for download to complete

**Expected Results**:
- ✅ Button shows loading spinner
- ✅ Button displays "Converting to MP3... 0%"
- ✅ Progress increases from 0 to 100
- ✅ Download starts automatically
- ✅ File is named "vocals.mp3" or similar
- ✅ File downloads successfully
- ✅ Progress indicator disappears after 2 seconds

**File Verification**:
- [ ] Open downloaded MP3 in media player
- [ ] Audio plays without errors
- [ ] Both vocals and accompaniment audible (verify correct stem)
- [ ] File size approximately 5.63 MB for 50 MB source

---

### Test 2.2: Multiple Format Downloads

**Steps**:
1. Select MP3 192k → Download vocals
2. While downloading, select OGG 128k (no click download yet)
3. When MP3 download finishes, click download vocals for OGG
4. Observe both downloads complete successfully

**Expected Results**:
- ✅ Can switch formats while downloading
- ✅ Each format shows independent progress
- ✅ Both downloads complete successfully
- ✅ Files have correct names (vocals.mp3 and vocals.ogg)

---

### Test 2.3: FLAC Download

**Steps**:
1. Select "FLAC" format (no bitrate selection)
2. Click "Download vocals"
3. Watch progress (should be ~8 seconds for 50 MB)
4. Verify download completes

**Expected Results**:
- ✅ Progress displays correctly for FLAC
- ✅ No bitrate selection in UI
- ✅ File named "vocals.flac"
- ✅ File size approximately 30 MB for 50 MB source
- ✅ Audio quality is lossless (can verify with audio analysis tools)

---

### Test 2.4: WAV Download

**Steps**:
1. Select "WAV" format
2. Click "Download accompaniment"
3. Observe progress (should complete almost instantly)

**Expected Results**:
- ✅ Progress shows 0% → 100% very quickly (<5 seconds)
- ✅ File named "accompaniment.wav"
- ✅ File size approximately 50 MB (same as source)
- ✅ Download completes very quickly (pass-through, no conversion)

---

### Test 2.5: OGG Download Both Bitrates

**Steps**:
1. Download vocals as OGG 128k
2. Then download accompaniment as OGG 192k
3. Verify both work and show different sizes

**Expected Results**:
- ✅ OGG 128k file: ~3.75 MB
- ✅ OGG 192k file: ~5.63 MB
- ✅ Both files download and play correctly
- ✅ OGG 192k has noticeably better audio quality

---

## Test Suite 3: Error Handling

### Test 3.1: Network Error Retry

**Simulate with DevTools**:
1. Open browser DevTools (Cmd+Shift+I)
2. Go to "Network" tab
3. Select "Offline" mode to simulate network failure
4. Click "Download vocals" with MP3 192k selected
5. Wait 5 seconds
6. Switch network back to "Online"

**Expected Results**:
- ✅ Download attempts fail initially
- ✅ Error message shows "retrying... (1/2)"
- ✅ Download retries automatically after 2 seconds
- ✅ After network is restored, retry succeeds
- ✅ File downloads successfully
- ✅ Progress shows completion

---

### Test 3.2: API Error Handling

**Test with invalid bitrate** (if backend allows):
1. Attempt to download with unsupported bitrate (if possible)
2. Observe error handling

**Expected Results**:
- ✅ Clear error message displayed to user
- ✅ Explains what went wrong
- ✅ Suggests corrective action if possible
- ✅ No progress spinner left spinning

---

### Test 3.3: Concurrent Downloads

**Steps**:
1. Select MP3 192k
2. Click "Download vocals"
3. While progress showing, click "Download accompaniment"
4. Let both complete

**Expected Results**:
- ✅ Both downloads start
- ✅ Each shows independent progress
- ✅ Both complete successfully
- ✅ Both files are correct

---

## Test Suite 4: UI/UX Validation

### Test 4.1: Button State During Download

**Steps**:
1. Start a download
2. Observe download buttons during export

**Expected Results**:
- ✅ Active download button shows spinner
- ✅ Inactive buttons are disabled/grayed out
- ✅ Format selector is disabled during export
- ✅ Cannot click other buttons while exporting

---

### Test 4.2: Progress Accuracy

**Steps**:
1. Download a file and manually time the conversion
2. Compare displayed progress vs actual time

**Expected Results**:
- ✅ Progress percentage is roughly accurate
- ✅ Doesn't jump wildly (smooth progression)
- ✅ Final 5 seconds show 95-100%
- ✅ No progress visualization lag

---

### Test 4.3: Error Message Display

**Steps**:
1. Trigger an error (network, format, etc.)
2. Observe error message display

**Expected Results**:
- ✅ Error message is visible and readable
- ✅ Appears in red/warning color
- ✅ Persists until user acknowledges
- ✅ Doesn't block other UI interactions

---

## Test Suite 5: File Format Verification

### Test 5.1: File Corruption Check

**For each downloaded file**:
```bash
# Check MP3
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1:nounits=1 vocals.mp3

# Check FLAC
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1:nounits=1 vocals.flac

# Check OGG
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1:nounits=1 vocals.ogg

# Check WAV
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1:nounits=1 vocals.wav
```

**Expected Results**:
- ✅ All files have valid durations
- ✅ Duration matches original file (approximately)
- ✅ No errors reported by ffprobe

---

### Test 5.2: Audio Quality Validation (Optional)

**For quality assessment**:
```bash
# Measure loudness (LUFS)
ffmpeg -i vocals.mp3 -af loudnorm=I=-23:TP=-1.5:LRA=7 -f null -

# Visual waveform analysis
sox vocals.wav vocals.png
```

**Expected Results**:
- ✅ MP3 files have consistent loudness with source
- ✅ FLAC is byte-perfect copy of source
- ✅ OGG has similar loudness to MP3
- ✅ WAV is identical to source

---

## Test Suite 6: Performance Benchmarks

### Test 6.1: Conversion Time - 5 Minute File

**File size: ~50 MB**

```
Format        Expected Time    Acceptable Range
──────────────────────────────────────────────
MP3 (128k)    20 seconds      15-30 seconds
MP3 (192k)    25 seconds      20-35 seconds
MP3 (320k)    35 seconds      25-45 seconds
FLAC          8 seconds       5-15 seconds
OGG (128k)    18 seconds      15-25 seconds
OGG (192k)    22 seconds      18-30 seconds
WAV           <1 second       <5 seconds
```

**Testing**:
1. Start conversion
2. Note start time
3. Wait for completion
4. Record actual time

**Acceptance Criteria**:
- [ ] MP3 conversions complete within 45 seconds
- [ ] FLAC completes within 15 seconds
- [ ] OGG completes within 30 seconds
- [ ] WAV completes within 5 seconds

---

### Test 6.2: Conversion Time - 10 Minute File

**File size: ~100 MB**

```
Format        Expected Time    Acceptable Range
──────────────────────────────────────────────
MP3 (192k)    50 seconds      40-60 seconds
FLAC          15 seconds      10-25 seconds
OGG (192k)    40 seconds      30-50 seconds
WAV           <2 seconds      <10 seconds
```

---

### Test 6.3: Conversion Time - 30 Minute File

**File size: ~300 MB**

```
Format        Expected Time    Acceptable Range
──────────────────────────────────────────────
MP3 (192k)    2 minutes       1.5-2.5 minutes
FLAC          45 seconds      30-60 seconds
OGG (192k)    2 minutes       1.5-2.5 minutes
WAV           <10 seconds     <30 seconds
```

---

## Browser Compatibility Testing

### Test Browsers

- [ ] Chrome/Edge (Latest)
- [ ] Firefox (Latest)
- [ ] Safari (Latest)

### Test Cases per Browser

- [ ] Format selector renders correctly
- [ ] Download buttons work
- [ ] Progress display shows
- [ ] Files download to default location
- [ ] localStorage works (DevTools → Application → localStorage)

---

## Accessibility Testing

- [ ] Format buttons have keyboard navigation (Tab to select)
- [ ] Download buttons are clearly labeled
- [ ] Progress percentage is announced to screen readers
- [ ] Error messages are announced
- [ ] Color contrast meets WCAG AA standards

---

## Summary Checklist

### Core Functionality
- [ ] FormatSelector component renders
- [ ] Format selection works (all 4 formats)
- [ ] Bitrate selection shows/hides correctly
- [ ] File size estimates display
- [ ] Conversion time estimates display

### Download Functionality
- [ ] Download button works for vocals
- [ ] Download button works for accompaniment
- [ ] Progress tracker displays percentage
- [ ] Conversion completes successfully
- [ ] Downloaded file has correct name

### Error Handling
- [ ] Network errors trigger retry
- [ ] Error messages display
- [ ] Multiple retries work
- [ ] User can recover from errors

### Performance
- [ ] MP3 conversions within 45 seconds (50MB)
- [ ] FLAC conversions within 15 seconds (50MB)
- [ ] OGG conversions within 30 seconds (50MB)
- [ ] WAV pass-through within 5 seconds (50MB)

### Data Persistence
- [ ] Format preference saved to localStorage
- [ ] Format restored after refresh
- [ ] No localStorage errors on browser storage full

### Quality
- [ ] Downloaded files play without errors
- [ ] Audio quality matches expected (lossy vs lossless)
- [ ] File sizes match estimates (±10%)
- [ ] Bitrate selection affects file quality

---

## Known Limitations & Future Work

### Current Implementation
- Single-threaded conversion (one at a time per file)
- Progress is estimated, not real-time from server
- No server-side caching of converted files
- No bandwidth throttling for large files

### Future Enhancements
- [ ] Server-side progress tracking via WebSocket
- [ ] Caching of recently converted files
- [ ] Batch download (download both stems as ZIP)
- [ ] Advanced format options (custom bitrates, etc.)
- [ ] Conversion queue with multiple concurrent conversions

---

**Test Report Template**:

```
Test Date: [DATE]
Tester: [NAME]
Test Environment: [OS/Browser/Version]
Test Audio File: [Duration/Size]

Results:
- Test Suite 1: [PASS/FAIL]
- Test Suite 2: [PASS/FAIL]
- Test Suite 3: [PASS/FAIL]
- Test Suite 4: [PASS/FAIL]
- Test Suite 5: [PASS/FAIL]
- Test Suite 6: [PASS/FAIL]

Overall: [PASS/FAIL]
Issues Found: [LIST]
```

