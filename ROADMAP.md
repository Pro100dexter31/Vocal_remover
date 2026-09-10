# Roadmap — Vocal Separator

Stare pe faze. Pentru business context vezi [BR.md](BR.md); pentru
task-uri granulare vezi [TASKS.md](TASKS.md).

## Faza 1 — Separare de bază ✅ Livrat
Upload fișier → Demucs → download vocals/accompaniment. Slider de
intensitate separare (0.0-1.0), acum ascuns din UI (default 0.5,
balansat) la cererea utilizatorului, dar funcțional în backend.

## Faza 2 — Export multi-format ✅ Livrat
Conversie la MP3 (128/192/320k)/FLAC/OGG/WAV la cerere, prin `/api/export`.

## Faza 3 — Normalizare volum ✅ Livrat
Normalizare peak (-1dBFS) sau LUFS (-14, standard YouTube/Spotify).
Volume meter în UI arată before/after real.

## Faza 4 — Preview live ✅ Livrat
Streaming audio cu HTTP range requests (seek), 4 moduri de preview:
Original / Vocals / Instrumental / Both (mixdown real, nu doar vocals).

## Faza 5 — Speed control ✅ Livrat
Ajustare viteză 0.5x-2.0x, pitch-invariant (librosa time-stretch), cache
per (fișier, viteză). Aplicabil atât la upload cât și post-hoc pe un
task deja separat.

## Faza 6 — Waveform comparison ✅ Livrat
Comparație vizuală Original/Vocals/Instrumental/Both, cu playhead live
în timpul redării, zoom, click-to-seek, paletă colorblind-safe.

## Faza 7 — YouTube → minus ✅ Livrat
Link YouTube → extragere audio (yt-dlp, audio-only, 320kbps) → aceeași
pipeline de separare ca la upload. Limită 15 min (verificată din
metadata, înainte de download). Progres pe 2 etape (downloading →
separating).

## Faza 8 — Schimbare tonalitate (pitch) pentru minus ✅ Livrat
Slider -6..+6 semitonuri pentru instrumentalul ("minus"). Preview "live":
fragment scurt de ~8s procesat sincron la calitate redusă (~200ms după
warmup numba), regenerat cu debounce cand utilizatorul mută slider-ul.
Buton separat "Pregătește pentru download" → job full-length async →
download. Se schimbă doar cheia muzicală, tempo-ul rămâne neschimbat
(librosa phase-vocoder). Doar pe minus, nu pe voce.

## Faza 9 — Neplanificat încă
Idei posibile, nu confirmate:
- Autentificare/istoric per utilizator (contrazice BR.md actual — de
  discutat dacă chiar se dorește)
- Procesare batch (mai multe fișiere/link-uri simultan)
- Export direct pe platforme externe (Spotify, SoundCloud)
- Suite de teste E2E automate pentru frontend (Playwright/Cypress) —
  în prezent doar verificare manuală + teste backend

## Limitări cunoscute, acceptate deliberat
- "Both (mixdown)" și "Original" nu trec prin normalizare/speed
  adjustment — sunt fișiere de preview/comparație, nu ținte de export
- Fără procesare GPU — rulează pe CPU, mai lent dar accesibil pe
  hardware modest
- Fără CI/CD automat — testele rulează manual (`pytest` în container)
