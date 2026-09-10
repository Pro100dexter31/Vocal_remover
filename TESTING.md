# Testing — Acoperire reală, verificată

Actualizat: 2026-09-10, rulat direct în containerul backend.
**Regulă**: orice cifră din acest fișier trebuie să vină din rularea
efectivă a comenzii de mai jos, nu din memorie sau presupunere — istoricul
acestui proiect are documente vechi care pretindeau "165+ teste" fără ca
`pytest` să fi fost vreodată instalat în imagine.

## Cum rulezi
```bash
docker exec vocal_remover-backend-1 python3 -m pytest backend/ -v
```
`pytest`/`pytest-mock` sunt instalate permanent (`requirements-dev.txt`,
în `backend/Dockerfile`) — nu necesită setup manual.

## Rezultat la ultima rulare
**137 teste, toate trec** (`137 passed`), ~1.5 minute.

## Acoperire pe fișier (backend, unit tests)

| Fișier | Teste | Acoperă |
|---|---|---|
| `test_audio_conversions.py` | 40 | Validare format/bitrate, conversii reale WAV→MP3/FLAC/OGG, estimare dimensiune, erori |
| `test_youtube_extractor.py` | 29 | Validare URL, metadata (mock), prag 15 min, download (mock) |
| `test_speed_adjuster.py` | 19 | Time-stretch, pitch invariance, cache, validare viteză |
| `test_pitch_shifter.py` | 19 | Pitch shift, tempo păstrat, f0 verificat (up/down), preview mode, validare -6..+6 |
| `test_speed_comprehensive.py` | 15 | Calitate/stabilitate pitch la toate vitezele, performanță, conținut spectral |
| `test_volume_normalizer.py` | 8 | Peak/LUFS, gain, RMS, edge cases |
| `test_converters_setup.py` | 6 | Sanity check mediu (librerii importabile, ffmpeg disponibil) |
| `test_separation_intensity.py` | 1 | Un singur test — **acoperire slabă aici, de extins** |

## Ce NU e acoperit de teste automate

- **Frontend**: zero teste automate (nici unit — Jest vine cu Create React
  App dar nu e folosit —, nici E2E — Playwright/Cypress absente).
  Verificarea frontend s-a făcut prin: build reușit (`docker compose build
  frontend`) + citire de cod + în unele cazuri testare manuală în browser
  de către utilizator.
- **Integrare completă upload→separare→download**: verificată manual, cu
  `curl`, în sesiuni de lucru (nu automatizată, nu rulează în CI pentru
  că necesită model Demucs + fișier audio real + minute de procesare)
- **CI/CD**: inexistent — testele rulează doar manual, la cerere

## Task-uri de testare rămase (candidate pentru extins)
1. `test_separation_intensity.py` — un singur test pentru un parametru
   cu impact mare (0.0/0.5/1.0 = comportamente foarte diferite)
2. Teste automate pentru `main.py` (endpoint-uri FastAPI) — în prezent
   verificate doar manual cu `curl`, niciun `TestClient` din FastAPI
3. Teste pentru `tasks.py` (`_run_separation_pipeline`,
   `process_youtube_task`) — logica de orchestrare Celery nu are teste
   unitare, doar verificare end-to-end manuală
4. Test automat pentru frontend (măcar smoke test: componentele se
   randează fără crash)

## Testare manuală E2E făcută (nu automatizată, dar reală)
Rulată cu fișiere audio reale și link-uri YouTube reale, rezultate
verificate cu `ffprobe`/`docker stats`, nu doar cod citit:
- Upload → separare → normalizare (peak + LUFS) → download
- Speed adjustment la upload și post-hoc, durată exactă verificată
- YouTube: extragere + separare completă, progres 2 etape, cleanup
- Memorie: ~1.9GB peak per job separare (upload sau YouTube, identic)
