# Feature 3: Quick Start Guide - Volume Normalization

**Ready to test?** Follow these steps to see Feature 3 in action.

---

## 🚀 Quick Setup

### Backend is Automatically Ready
- Volume normalizer module is already integrated
- Normalization runs automatically after separation
- Default: ON (enabled by default)

### Frontend is Ready
- Checkbox appears in upload zone
- Default: Checked (normalization enabled)
- Can toggle ON/OFF before upload

---

## 🧪 Testing the Feature

### Test 1: Quiet Audio with Normalization (5 minutes)

1. **Prepare a quiet audio file** (low volume, hard to hear)
   - Use existing audio or create test file
   - Keep normalization checkbox ON

2. **Upload and Process**
   - Upload audio file
   - Wait for separation to complete
   - Behind scenes: Normalization applied automatically

3. **Download and Verify**
   - Download both vocals and accompaniment
   - Open in media player
   - Listen: Volume should be normalized/louder
   - No distortion should occur

4. **Expected Result**
   - ✅ Audio is louder than original
   - ✅ No clipping/distortion
   - ✅ Consistent with other downloads

---

### Test 2: Loud Audio (Clipping Prevention) (5 minutes)

1. **Prepare loud audio file** (might have distortion risk)
   - Use audio that peaks near maximum
   - Keep normalization ON

2. **Upload and Process**
   - Upload audio
   - Separation begins
   - Normalization prevents potential clipping

3. **Verify Prevention**
   - Download stems
   - Play in audio editor (Audacity, etc)
   - Check waveform: Should have headroom
   - No visible clipping

4. **Expected Result**
   - ✅ No audio distortion
   - ✅ Safe headroom (-1dB peak)
   - ✅ Professional quality

---

### Test 3: Disable Normalization (5 minutes)

1. **Uncheck Normalization**
   - Before uploading audio
   - Uncheck "Auto Normalize Volume"

2. **Upload and Process**
   - Upload audio
   - Wait for separation
   - No normalization applied

3. **Compare Results**
   - Download with normalization OFF
   - Compare to previous downloads (normalization ON)
   - Should hear difference in volume level

4. **Expected Result**
   - ✅ Audio volume unchanged
   - ✅ Preference respected
   - ✅ Can toggle ON/OFF anytime

---

### Test 4: Preference Persistence (5 minutes)

1. **Set Normalization to OFF**
   - Uncheck "Auto Normalize Volume"
   - Upload and process audio

2. **Refresh Page**
   - Press Cmd+R (Mac) or F5 (Windows)
   - Wait for page to reload
   - After processing completes again...

3. **Verify Preference**
   - Checkbox should still be UNCHECKED
   - Normalization preference was saved ✅

4. **Expected Result**
   - ✅ localStorage persists preference
   - ✅ User doesn't need to re-toggle
   - ✅ Good UX

---

## 📊 What to Listen For

### With Normalization (Default)
- Audio is loud and clear
- No distortion or clipping
- Consistent level across uploads
- Professional sound

### Without Normalization
- Audio level varies by source
- Quiet files sound quiet
- Loud files might distort if already loud
- Natural/raw output

---

## 🎯 Technical Details

### Peak Normalization Target
- **Target**: -1dB peak
- **Why**: Prevents clipping, leaves headroom
- **Amplitude**: 0.891 (out of 1.0)

### LUFS (Loudness) Support
- **Estimated**: Based on RMS calculation
- **YouTube Standard**: -14 LUFS
- **Currently Used**: Peak method (-1dB)

### Processing Location
```
Upload → Separation → [NEW] Normalization → Export → Download
```

### Performance
- **Time Added**: 2-5 seconds per stem
- **Negligible**: Compared to 30-90s separation
- **Optional**: Can disable if not needed

---

## 📁 Key Implementation Files

### Backend:
- `backend/volume_normalizer.py` (400 lines)
  - Peak detection
  - Gain calculation
  - LUFS support
  
- `backend/tasks.py` (modified)
  - Added normalize parameter
  - Calls _apply_normalization()
  
- `backend/main.py` (modified)
  - /api/upload accepts normalize flag

### Frontend:
- `frontend/src/App.jsx` (modified)
  - Normalize checkbox in UI
  - localStorage persistence
  - Sends normalize with upload

### Testing:
- `backend/test_volume_normalizer.py` (500 lines)
  - 8 test suites
  - 40+ test cases
  - All scenarios covered

---

## 🐛 Troubleshooting

**Q: Checkbox isn't appearing**
- A: Refresh page, hard refresh (Cmd+Shift+R)

**Q: Preference not saving**
- A: Check browser console for errors
- A: Try incognito mode to test

**Q: Normalization not working**
- A: Check backend logs
- A: Ensure audio file is valid WAV/MP3

**Q: Audio sounds different**
- A: That's expected! Normalization changes volume
- A: Disable to compare

**Q: Processing slower**
- A: Normal, adds 2-5s per stem
- A: Disable if speed is priority

---

## ✅ Quality Checklist

### Does This Work?
- [ ] Checkbox appears in UI
- [ ] Can toggle ON/OFF
- [ ] Preference saves to localStorage
- [ ] Quiet audio becomes louder
- [ ] Loud audio stays safe (no clipping)
- [ ] Can disable if needed
- [ ] Processing completes successfully
- [ ] Downloaded audio sounds good

---

## 🎬 Demo Scenario (10 minutes)

**Perfect for showing Feature 3 to stakeholders:**

1. **Show UI** (1 min)
   - Point out "Auto Normalize Volume" checkbox
   - Explain: "Prevents distortion and ensures consistent loudness"

2. **Disable Normalization** (1 min)
   - Uncheck the checkbox
   - Explain: "Users can disable if they want raw output"

3. **Upload Quiet Audio** (1 min)
   - Show a deliberately quiet audio file

4. **Process** (5 min)
   - Wait for separation to complete
   - Show progress

5. **Download and Compare** (2 min)
   - Download one stem
   - Open in media player
   - Play: "Hear how the volume is normalized?"
   - Show waveform in editor: "Safe -1dB peak"

6. **Summary** (1 min)
   - Prevents audio clipping
   - Ensures consistent loudness
   - Optional (can toggle off)
   - No quality loss

---

## 🎵 Success Criteria

Feature 3 is working correctly when:

✅ Checkbox appears in UI (upload zone)
✅ Default state: ON (checked)
✅ Can toggle ON and OFF
✅ Preference saves to localStorage
✅ Quiet audio normalized (louder)
✅ Loud audio protected (no clipping)
✅ Download sounds good
✅ No processing errors
✅ No console errors
✅ Runs quickly (adds <5s)

---

## 🚀 Next Steps

After Feature 3 testing:
1. Verify all 3 features work together
2. Test with real user scenarios
3. Get user feedback
4. Consider future enhancements

---

**Happy Testing! 🎵**

For complete technical details, see `FEATURE_3_VOLUME_NORMALIZATION_SUMMARY.md`

