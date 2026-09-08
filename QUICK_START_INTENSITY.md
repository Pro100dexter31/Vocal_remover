# Quick Start: Separation Intensity Feature

## What is it?

The **Separation Intensity** slider lets you control how much vocal presence you want in the processed audio.

## How to Use

### Step 1: Open the App
Visit http://localhost:3000 in your browser

### Step 2: Adjust the Slider
Before uploading, use the **"Separation Level"** slider to set your desired intensity:

```
← More Instrumental ────●──────── More Vocals →
                    [Slider here]
                  Vocal Level: 50%
```

### Step 3: Choose Your Setting

| Setting | Use Case | What You Hear |
|---------|----------|--------------|
| **0%** | Perfect for creating karaoke tracks | Pure instrumental, no vocals at all |
| **25%** | Backing track with vocal hints | Mostly instrumental, faint vocal presence |
| **50%** (Default) | General purpose, balanced separation | Clear vocal and instrumental separation |
| **75%** | Extracting acapella with context | Strong vocals with instrumental hints |
| **100%** | Maximum vocal emphasis | Loudest possible vocals from the mix |

### Step 4: Upload and Process
1. Set your desired intensity level
2. Click "Choose audio file" or drag-and-drop your audio
3. Wait for processing to complete
4. Download the processed stems

### Step 5: Download Results

You'll get two files:
- **Voce izolată** (Vocals) - Intensity affects this file most
- **Minus (fără voce)** (Accompaniment) - Relatively unchanged

---

## Tips & Tricks

### Finding Your Perfect Level

1. **First time**: Start with 50% (default)
2. **Need more vocals?**: Move to 75% or 100%
3. **Want cleaner instrumental?**: Try 0% or 25%
4. **Test multiple levels**: Upload same song at different intensities to find sweet spot

### Saving Your Preference

- Your last used intensity is automatically saved
- Next time you open the app, it starts at your preferred level
- Clear browser data to reset to default 50%

### Expected Audio Quality

✅ No quality loss due to intensity adjustment
✅ All outputs are MP3 at 192 kbps
✅ Processing time is the same regardless of intensity
✅ File sizes are identical

---

## Comparing Results

### How to Compare Different Intensities

**Method 1: Download Multiple**
1. Upload at 0%, download vocals
2. Upload same song at 50%, download vocals
3. Upload same song at 100%, download vocals
4. Listen to all three to hear the difference

**Method 2: A/B Testing**
1. Keep browser tabs open
2. Listen to 0% in one tab, 100% in another
3. Switch between tabs to compare

**Expected Differences**:
- **At 0%**: Vocals track is very quiet/minimal
- **At 50%**: Vocals track is clear and balanced
- **At 100%**: Vocals track is prominent and loud

---

## Common Questions

### Q: Does intensity affect processing time?
**A**: No. Processing takes the same time regardless of intensity setting.

### Q: Will my audio quality change?
**A**: No. The intensity adjustment is applied after separation and doesn't affect quality.

### Q: Can I change intensity after downloading?
**A**: No. You need to re-upload and process at the new intensity level.

### Q: What's the difference between 75% and 100%?
**A**: The vocal presence increases smoothly. 100% gives maximum vocal content available.

### Q: Why does my 0% output still have some vocals?
**A**: Demucs separation isn't 100% perfect. Some vocal artifacts may remain even at 0% intensity.

### Q: Should I use 100% or 0%?
**A**: It depends on your use case:
- Use **0%** for backing tracks/karaoke
- Use **100%** for vocal extraction/emphasis
- Use **50%** for balanced separation (most common)

---

## Troubleshooting

### My slider value doesn't save
- **Fix**: Check if cookies/localStorage are enabled in your browser
- **Fix**: Try clearing browser cache and reloading

### I don't see the slider
- **Fix**: Try refreshing the page (Ctrl+R or Cmd+R)
- **Fix**: Check that you're on the latest version of the app

### My upload fails
- **Fix**: Make sure your intensity value sent correctly (0-100%)
- **Fix**: Check file size is under 500 MB
- **Fix**: Try with a different audio file

### I can't hear the difference
- **Fix**: Download at 0% AND 100% to hear maximum difference
- **Fix**: Listen with good quality headphones/speakers
- **Fix**: The differences are sometimes subtle

---

## Best Practices

✅ **DO**:
- Test with your actual use case audio
- Start with 50% if unsure
- Use 0% for clean instrumental tracks
- Use 100% for maximum vocal extraction

❌ **DON'T**:
- Expect 100% perfect vocal removal (it's AI-based)
- Use extreme values if you want subtle separation
- Forget to download both stems (vocals AND accompaniment)

---

## Getting Help

If something doesn't work:

1. **Clear your browser cache**: Ctrl+Shift+Delete (Chrome/Firefox) or Cmd+Shift+Delete (Safari)
2. **Reload the page**: Ctrl+R or Cmd+R
3. **Try a different audio file**: Some files separate better than others
4. **Check server status**: If uploads fail repeatedly, the backend may be down

---

## Examples

### Example 1: Creating a Karaoke Track
```
Desired intensity: 0% (maximum instrumental)
Steps:
1. Set slider to 0%
2. Upload your song
3. Download "Minus (fără voce)"
4. Use as backing track
```

### Example 2: Extracting Vocals
```
Desired intensity: 75-100% (maximum vocals)
Steps:
1. Set slider to 100%
2. Upload your song
3. Download "Voce izolată"
4. Use for vocal processing
```

### Example 3: General Purpose Separation
```
Desired intensity: 50% (balanced, default)
Steps:
1. Use default 50% setting
2. Upload your song
3. Download both files
4. Mix and edit as needed
```

---

## What Happens Behind the Scenes

When you upload:
1. ✓ Your intensity setting is sent with the file
2. ✓ Backend receives intensity (0.0-1.0)
3. ✓ Demucs separates vocals and instrumental
4. ✓ Intensity blending is applied to vocals
5. ✓ Files are saved and ready for download

**Total processing time**: 30 seconds to 5 minutes (depending on song length)

---

## Feedback

If you have suggestions or found a bug:
- Report issue on GitHub
- Include:
  - What intensity level you used
  - What audio file you tested with
  - What result you got vs expected

---

**Happy separating! 🎵**
