# 🎵 Vocal Separator - Implementation Roadmap (7 Features)

## Instrucțiuni Generale
Pentru fiecare feature, vei implementa taskurile în ordine. Testează după fiecare task. Raportează blocaj-uri imediat.

---

## 📋 FEATURE 1: Adjustable Separation Levels (Slider 0-100%)

### Descriere
Permite utilizatorului să controleze intensitatea vocală în output-ul final. La 0%, instrumentalul este maxim; la 100%, vocalurile sunt maxime.

### Task 1.1: Backend - Parametru pentru separation intensity
- [ ] Modifică model-ul Spleeter pentru a accepta un parametru `separation_intensity` (0.0 - 1.0)
- [ ] Implementează logica: valorile sliderului (0-100) se mapează la 0.0-1.0
- [ ] Testează cu valori: 0, 25, 50, 75, 100
- [ ] Documentează cum afectează output-ul

### Task 1.2: Frontend - UI Slider Component
- [ ] Creează un React component `SeparationLevelSlider`
- [ ] Slider: min=0, max=100, default=50, step=1
- [ ] Afișează valoarea curentă (ex: "Vocal Level: 50%")
- [ ] Actualizează state în real-time pe schimbare
- [ ] Adaugă labels: "More Instrumental" ← → "More Vocals"

### Task 1.3: Integration - Connect slider to processing
- [ ] Trimite `separation_intensity` cu request-ul de procesare
- [ ] Backend aplică parametrul înainte de export
- [ ] Testează: descarcă rezultatele la 0%, 50%, 100%
- [ ] Verifică că outputul se schimbă corespunzător

### Task 1.4: UX Improvements
- [ ] Adaugă preset buttons: "Vocals Only", "Balanced", "Instrumental Only"
- [ ] Salvează ultima valoare folosită în localStorage
- [ ] Adaugă tooltip: "Adjust to get the perfect balance"

---

## 🎵 FEATURE 2: Export Multiple Formats (MP3, WAV, FLAC, OGG)

### Descriere
Permite download-ul fișierului în mai multe formate audio, nu doar WAV.

### Task 2.1: Backend - Setup converters
- [ ] Instalează librării necesare:
  - `pydub` (pentru conversii de bază)
  - `librosa` (audio processing)
  - `soundfile` (pentru FLAC)
- [ ] Configurează paths pentru ffmpeg (dacă e necesar)
- [ ] Testează instalarea

### Task 2.2: Backend - Conversion functions
- [ ] Creează funcția `convert_audio(input_path, output_format, bitrate)`
- [ ] Implementează conversii pentru:
  - [ ] WAV → MP3 (128 kbps, 192 kbps, 320 kbps options)
  - [ ] WAV → FLAC (lossless)
  - [ ] WAV → OGG (128 kbps, 192 kbps)
- [ ] Handlează errors (format invalid, file corrupted, etc.)
- [ ] Testează fiecare conversie manual

### Task 2.3: Backend - API Endpoint
- [ ] Creează endpoint: `POST /api/export?format=mp3&bitrate=320`
- [ ] Acceptă: `format` (string), `bitrate` (optional, int)
- [ ] Validează format-ul (whitelist: mp3, wav, flac, ogg)
- [ ] Returneaza file-ul cu header corect: `Content-Disposition: attachment; filename="file.mp3"`

### Task 2.4: Frontend - Format Selector
- [ ] Creează component `FormatSelector`
- [ ] Dropdown/Buttons pentru a selecta format
- [ ] Dacă MP3/OGG, arată și bitrate options (128, 192, 320 kbps)
- [ ] Arată dimensiunea estimată a fișierului pentru fiecare format
- [ ] Default: WAV (lossless quality)

### Task 2.5: Frontend - Download Logic
- [ ] Modifica download button pentru a trimite format la backend
- [ ] Afișează loading spinner cu text: "Converting to MP3... (30%)"
- [ ] Estimează durata conversiei base pe file size
- [ ] Handle errors și retry logic
- [ ] Salvează format preferat în localStorage

### Task 2.6: Testing & Optimization
- [ ] Testează download pentru fiecare format (verifică corruption)
- [ ] Compară file sizes: WAV vs MP3 vs FLAC vs OGG
- [ ] Măsoară conversion time la file de 5min, 10min, 30min
- [ ] Optimizează dacă conversiile sunt prea lente

---

## 🔊 FEATURE 3: Volume Normalization

### Descriere
Normalize automat volumul output-ului pentru a evita clipping și pentru consistență.

### Task 3.1: Backend - Normalization Algorithm
- [ ] Implementează normalization function:
  ```
  - Detectează peak volume
  - Calculează gain factor pentru a-l aduce la -1dB
  - Aplică gain factor la entire audio
  ```
- [ ] Folosește librosa/scipy pentru peak detection
- [ ] Testează cu fișiere loud și quiet

### Task 3.2: Backend - LUFS Loudness Standard (Optional Advanced)
- [ ] Implementează LUFS metering (loudness standard pentru streaming)
- [ ] Target: -14 LUFS (YouTube standard)
- [ ] Aplică normalization pentru a ajunge la target
- [ ] Testează cu audio de la diferite surse

### Task 3.3: Backend - Integration în processing pipeline
- [ ] Aplică normalization DUPĂ separation și ÎNAINTE de export
- [ ] Adaugă flag: `normalize: true/false`
- [ ] Testează că normalization nu afectează calitatea

### Task 3.4: Frontend - Normalization Toggle
- [ ] Checkbox: "Auto Normalize Volume"
- [ ] Default: ON
- [ ] Tooltip: "Prevents distortion and ensures consistent loudness"
- [ ] Salvează preferință în settings

### Task 3.5: Frontend - Volume Meter (Visual)
- [ ] Afișează volume level în dB înainte și după normalization
- [ ] Graphic bar: -20dB (quiet) → 0dB (clipping)
- [ ] Color coding: Green (safe), Yellow (approaching max), Red (clipping)

### Task 3.6: Testing
- [ ] Testează normalization cu audio: quiet, normal, loud
- [ ] Verifică că nu e clipping după normalization
- [ ] Compară perceived loudness cu/fără normalization

---

## 🎧 FEATURE 4: Real-time Preview (3 Modes)

### Descriere
Ascultă instrumentalul, vocalurile, sau ambele direct din UI înainte de download. Fără a fi necesar să downloadezi tot.

### Task 4.1: Backend - Streaming Audio Endpoint
- [ ] Creează endpoint: `GET /api/preview?type=vocals|instrumental|both&file_id=xxx`
- [ ] Implementează streaming în loc de download complet
- [ ] Suportă HTTP range requests pentru seeking
- [ ] Testează cu fișiere de 5-30 min

### Task 4.2: Backend - Audio Buffering
- [ ] Buffuiază primele 30 secunde pentru rapid preview
- [ ] După 30sec, stream rest-ul audio-ului
- [ ] Handleaza disconnect și resume

### Task 4.3: Frontend - Audio Player Component
- [ ] Creează `PreviewPlayer` component cu 3 butoane:
  - [ ] "Preview Vocals"
  - [ ] "Preview Instrumental"  
  - [ ] "Preview Both (Mixed)"
- [ ] Standard HTML5 `<audio>` element cu controls
- [ ] Progress bar, play/pause, volume control
- [ ] Timp curent și durata totală

### Task 4.4: Frontend - Multiple Players Management
- [ ] Setare: o singură preview se poate reda la un moment
- [ ] Dacă userul apasă alt preview, stop-ul pe celui anterior
- [ ] Arată indicator care preview-ul este activ

### Task 4.5: Frontend - Visual Feedback
- [ ] Loading spinner în timp ce se buffuiază
- [ ] Waveform visualization (basic canvas) care se animează
- [ ] Afișează: "Preview loaded" vs "Loading..." vs "Stream interrupted"
- [ ] Butoane dezactivate dacă se încă procesează

### Task 4.6: Testing & Optimization
- [ ] Testează preview cu diferite viteze internet (3G, 4G, WiFi)
- [ ] Testează disconnect și reconnect behavior
- [ ] Măsoară bandwidth folosit pentru preview (trebuie să fie mic)
- [ ] Verifica calitatea audio-ului (nu pixelat, fără popping)

---

## ⏱️ FEATURE 5: Speed Control (0.5x - 2.0x)

### Descriere
Permite utilizatorului să accelereze/încetinească output-ul (pitch invariant - doar viteza se schimbă).

### Task 5.1: Backend - Speed Adjustment
- [ ] Implementează time-stretching folosind librosa:
  ```python
  librosa.effects.time_stretch(y, rate=speed_factor)
  ```
- [ ] Acceptă speeds: 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x
- [ ] Testează că pitch-ul NU se schimbă (time-stretch invariant)

### Task 5.2: Backend - Processing Optimization
- [ ] Time-stretching e computationally expensive
- [ ] Cache rezultate dacă acelasi file + acelasi speed
- [ ] Estimează durata processing: ~2x durata audio
- [ ] Testează cu file de 10+ minute

### Task 5.3: Backend - API Endpoint
- [ ] Endpoint: `POST /api/process?speed=1.5`
- [ ] Validează speed (0.5 - 2.0)
- [ ] Returneaza status: processing, completed, failed

### Task 5.4: Frontend - Speed Selector
- [ ] Creează component `SpeedControl`
- [ ] Buttons: 0.5x, 0.75x, 1.0x (default), 1.25x, 1.5x, 2.0x
- [ ] Arată durata aproximativă după speed change (ex: "Original: 10min → New: 5min at 2.0x")
- [ ] Visual indicator pentru speed curent

### Task 5.5: Frontend - Preview with Speed
- [ ] Permite preview-ului să arate și speed-ul selectat
- [ ] Ascultă instrumentalul la 1.5x pentru a vedea cum sună
- [ ] Actualizează durata în player-ul de preview

### Task 5.6: Frontend - Settings Persistence
- [ ] Salvează speed preferat în localStorage
- [ ] Aplică automat la viitoarele uploads

### Task 5.7: Testing
- [ ] Testează fiecare speed: verifică calitate, pitch stability
- [ ] Compara timp processing: 1x vs 2x
- [ ] Verifică că audio nu e distorsionat la extreme (0.5x, 2.0x)

---

## 📊 FEATURE 6: Before/After Comparison (Waveform Visual)

### Descriere
Afișează vizual waveformurile originale vs vocals vs instrumental. Permite comparație ușor.

### Task 6.1: Backend - Waveform Data Generation
- [ ] Genereaza waveform data (pentru display eficient)
- [ ] Calculeaza RMS values pe chunks de 512 samples
- [ ] Returneaza JSON cu peaks și valleys per chunk
- [ ] Endpoint: `GET /api/waveform?file_id=xxx&type=original|vocals|instrumental`
- [ ] Cache-aza waveform data pentru viitoare requests

### Task 6.2: Frontend - Waveform Component (Canvas/SVG)
- [ ] Creează `WaveformComparison` component
- [ ] 3 waveforms pe vertical:
  - [ ] Original (gri)
  - [ ] Vocals (roșu/albastru)
  - [ ] Instrumental (verde/portocaliu)
- [ ] Zoom functionality (scroll sau slider pentru zoom)
- [ ] Scroll orizontal pentru a naviga prin audio
- [ ] Synchronous scrolling între toți 3 waveforms

### Task 6.3: Frontend - Interactive Features
- [ ] Hover pe waveform pentru a vedea time + amplitude
- [ ] Click pe waveform pentru a sări la acel timp în preview player
- [ ] Highlight current play position cu vertical line
- [ ] Color-coded legends sub fiecare waveform

### Task 6.4: Frontend - Statistics Panel
- [ ] Afișează stats pentru fiecare stem:
  - Peak volume (dB)
  - RMS loudness
  - Durata
  - File size
- [ ] Format: tabel simplu
- [ ] Comparare side-by-side: Original vs Processed

### Task 6.5: Frontend - Responsive Design
- [ ] Pe mobile: stack waveforms vertical
- [ ] Waveform responsive (se scalează cu screen)
- [ ] Zoom buttons pentru mobile (+ și -)

### Task 6.6: Performance Optimization
- [ ] Waveform rendering trebuie să fie instant (<100ms)
- [ ] Use RequestAnimationFrame pentru smooth scrolling
- [ ] Lazy load waveforms (nu încarca dacă user nu face click pe tab)

### Task 6.7: Testing & Polish
- [ ] Testează cu fișiere de 1min, 10min, 30min
- [ ] Verifica acuratețea waveform vs audio real
- [ ] UI clarity: ușor de înțeles care e care?
- [ ] Accessibility: colors accessible (colorblind friendly)

---

## 🧪 INTEGRATION & TESTING

### Task I1: End-to-End Workflow Testing
- [ ] Upload audio → ajusteaza slider → selecteaza format → download
- [ ] Upload audio → preview vocals/instrumental → ajusteaza speed → download
- [ ] Upload audio → compara waveforms → download
- [ ] Testează cu 3+ genuri de muzică (Pop, Classical, Hip-hop)

### Task I2: Error Handling
- [ ] Testează cu file corrupt, neaudio, prea mare
- [ ] Implementează error messages user-friendly
- [ ] Retry logic pentru network failures
- [ ] Timeout handling pentru processing prea lung

### Task I3: Performance Profiling
- [ ] Măsoară response time pentru fiecare feature
- [ ] Identifică bottlenecks (backend vs frontend)
- [ ] Optimizează dacă necesaro (caching, parallelization)
- [ ] Test load: simulează 10+ users concurrent

### Task I4: Browser Compatibility
- [ ] Testează pe: Chrome, Firefox, Safari, Edge
- [ ] Audio player compatibility
- [ ] Canvas/Waveform rendering pe toți browsers

---

## 📝 DOCUMENTATION & DELIVERY

### Task D1: Code Documentation
- [ ] Comentează toate functiile noi
- [ ] Creează README cu feature descriptions
- [ ] Backend API docs (Swagger/OpenAPI)

### Task D2: User Guide
- [ ] Screenshots pentru fiecare feature
- [ ] Step-by-step guide
- [ ] Troubleshooting section

### Task D3: Demo & Presentation
- [ ] Record 2-3 min demo video
- [ ] Highlight toate 7 features
- [ ] Before/after audio comparison

---

## 🎯 PRIORITIZATION GUIDE
**Week 1-2:** Features 2, 3 (foundational)
**Week 2-3:** Features 1, 5 (enhancement)
**Week 3-4:** Features 4, 6 (advanced UI)

---

## ⚙️ TECH STACK ASSUMPTIONS
- **Backend:** Python (Flask/FastAPI), librosa, pydub, soundfile
- **Frontend:** React, HTML5 Audio API, Canvas
- **Database:** (pentru history, optional)

**Adaptează prompt-ul de mai sus dacă stack-ul e diferit!**
