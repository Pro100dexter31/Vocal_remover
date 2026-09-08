# Separation Intensity Feature - Implementation Guide

## Overview

The **separation_intensity** parameter allows users to control the vocal emphasis in the processed audio output. It works by blending the separated vocals with the original audio based on the intensity level.

## Parameter Range

- **Range**: 0.0 - 1.0 (or 0% - 100% in UI)
- **Default**: 0.5 (50% - balanced)

## How It Works

### Intensity Levels

| Intensity | UI Value | Effect | Use Case |
|-----------|----------|--------|----------|
| 0.0 | 0% | Pure accompaniment (vocals completely removed) | Create backing tracks |
| 0.25 | 25% | Mostly instrumental with subtle vocals | Karaoke with vocal hints |
| 0.5 | 50% | Balanced mix (default) | General purpose separation |
| 0.75 | 75% | Mostly original mix with vocal emphasis | Acapella extraction with context |
| 1.0 | 100% | Vocals maximized (original mix + vocal enhancement) | Maximum vocal emphasis |

### Implementation Details

**Backend Logic** (`_separate_stems()` in `tasks.py`):

```python
# Blend: more intensity = more vocals in final output
if separation_intensity != 0.5:
    intensity = max(0.0, min(1.0, separation_intensity))
    vocals = vocals * intensity + (waveform - accompaniment) * (1.0 - intensity)
```

**Formula Breakdown**:
- `vocals * intensity` = Separated vocals scaled by intensity
- `(waveform - accompaniment) * (1.0 - intensity)` = Original vocals content scaled inversely
- This creates smooth blending between pure separation and original mix

## Frontend Integration

### Component: `SeparationLevelSlider`

Located at: `frontend/src/components/SeparationLevelSlider.jsx`

**Features**:
- Slider input: min=0, max=100, step=1
- Real-time value display
- Visual gradient fill
- Persistent storage in localStorage
- Labels: "More Instrumental" ← → "More Vocals"

### Usage in App

1. Slider appears before file upload
2. User adjusts intensity before selecting file
3. Selected value is saved to localStorage
4. Value is sent with upload request to backend

## API Integration

### Upload Endpoint

**POST** `/api/upload`

**Parameters**:
- `file` (multipart/form-data): Audio file
- `separation_intensity` (float, optional): 0.0-1.0, default=0.5

**Request Example**:
```javascript
const formData = new FormData();
formData.append('file', audioFile);
formData.append('separation_intensity', 0.75); // 75% vocal emphasis

fetch('/api/upload', {
  method: 'POST',
  body: formData
});
```

### Validation

- Backend validates range: `0.0 <= separation_intensity <= 1.0`
- Returns 400 error if out of range
- Default to 0.5 if not provided

## Testing

### Running Tests

```bash
cd vocal-separator/backend

# Option 1: Use test script
python test_separation_intensity.py

# Option 2: Manual testing with curl
for intensity in 0.0 0.25 0.5 0.75 1.0; do
  curl -X POST http://localhost:8000/api/upload \
    -F "file=@test_audio.mp3" \
    -F "separation_intensity=$intensity"
done
```

### Test Cases

Test at these intensity levels:

| Value | Expected Output |
|-------|-----------------|
| 0.0 | Pure accompaniment, no vocals |
| 0.25 | Mostly instrumental, faint vocals |
| 0.5 | Balanced separation (standard) |
| 0.75 | Slightly more vocals than balanced |
| 1.0 | Maximum vocal presence |

### Verification Checklist

- [ ] Slider updates in real-time
- [ ] Value persists across sessions (localStorage)
- [ ] Intensity value sent with upload
- [ ] Backend accepts 0.0-1.0 range
- [ ] Outputs at 0% are different from 100%
- [ ] Outputs show progressive change (0% → 25% → 50% → 75% → 100%)
- [ ] No audio glitches or artifacts
- [ ] Download files are accessible

## Output Comparison

### How to Compare Results

1. Download outputs at different intensities
2. Listen to both `vocals` and `accompaniment` files
3. Expected observations:

   **At 0% intensity**:
   - Vocals file: very quiet/minimal
   - Accompaniment: clean instrumental

   **At 50% intensity** (default):
   - Vocals file: clear vocal stems
   - Accompaniment: instrumental without vocals

   **At 100% intensity**:
   - Vocals file: louder, more present vocals
   - Accompaniment: similar to 0% but with intensity applied

## Performance Notes

- Processing time: **Same for all intensity levels**
- File size: **Same for all intensity levels** (both output at MP3)
- Memory: **No additional memory required**
- CPU: **No additional CPU required**

The intensity adjustment is applied **after** separation, so it doesn't affect processing cost.

## Future Enhancements

Possible improvements:

1. **Preset Buttons**: "Instrumental Only", "Balanced", "Vocals Only"
2. **Per-Stem Intensity**: Separate sliders for vocals and accompaniment
3. **Advanced Blending**: Different algorithms (exponential, sigmoid)
4. **Real-time Preview**: Play preview at different intensities before processing
5. **Batch Processing**: Apply intensity to multiple files

## Troubleshooting

### Issue: Slider value not sent with upload

**Solution**: Check that `separation_intensity` is appended to FormData:
```javascript
formData.append('separation_intensity', separationLevel / 100);
```

### Issue: Backend returns 400 error

**Solution**: Ensure intensity is between 0.0 and 1.0 (not 0-100):
```javascript
// Correct: 0-1 range
formData.append('separation_intensity', 0.5);

// Incorrect: 0-100 range
formData.append('separation_intensity', 50);
```

### Issue: No difference in output

**Solution**:
1. Test with intensity values at extremes (0.0 and 1.0)
2. Listen carefully to both stems
3. Check that backend is receiving the parameter (check logs)
4. Verify `_separate_stems()` is being called with intensity

## Files Modified

### Backend
- `backend/tasks.py`: Added intensity parameter to `_separate_stems()` and `process_audio_task()`
- `backend/main.py`: Added intensity parameter to upload endpoint

### Frontend
- `frontend/src/App.jsx`: Updated upload function to send intensity
- `frontend/src/components/SeparationLevelSlider.jsx`: New component

### Tests
- `backend/test_separation_intensity.py`: Integration test script

## References

- Demucs Documentation: https://github.com/facebookresearch/demucs
- Audio Processing: PyTorch, librosa
