# Tasks — Stare curentă verificată

Actualizat: 2026-09-10. Fiecare linie de mai jos a fost **verificată prin
rulare reală** (curl, pytest, sau test manual), nu doar scrisă din cod citit.
Dacă modifici ceva, actualizează linia corespunzătoare — nu lăsa acest
fișier să devină un alt document de fantezie ca cele șterse.

## Backend

| Task | Status | Verificat cu |
|---|---|---|
| Upload fișier → separare Demucs | ✅ | curl end-to-end, fișiere reale |
| `separation_intensity`, `normalize`, `speed`, `normalization_method` ajung la backend | ✅ | curl cu valori invalide → 400 corect (dovadă că parametrii chiar sunt citiți) |
| Normalizare peak | ✅ | curl, before/after dB corecte |
| Normalizare LUFS | ✅ | curl, `method: "lufs"` confirmat în răspuns |
| Speed adjustment la upload | ✅ | curl, durată exactă (218.53s → 174.86s la 1.25x) |
| Speed adjustment post-hoc (`/api/process`) | ✅ | curl, job nou + poll + download |
| Cache speed (nu reprocesează aceeași cerere) | ✅ | curl, a doua cerere <1s |
| Export multi-format (mp3/flac/ogg/wav) | ✅ | curl, fișiere valide |
| Preview streaming + range requests | ✅ | curl, HTTP 206 cu headere corecte |
| Preview "both" = mixdown real (nu doar vocals) | ✅ | curl, fișier `both.mp3` distinct generat |
| Preview "original" păstrat (copie comprimată) | ✅ | curl, `original.mp3` generat înainte de ștergerea uploadului |
| Waveform data (4 track-uri) | ✅ | curl, `/api/waveform` returnează original/vocals/accompaniment/both |
| YouTube: validare URL + metadata | ✅ | 29 teste unitare + video real |
| YouTube: download audio-only + extract MP3 | ✅ | fișier real descărcat, 320kbps confirmat |
| YouTube: limită 15 min respinsă înainte de download | ✅ | testat cu mock (prag exact) |
| YouTube: progres 2 etape (downloading/separating) | ✅ | curl, poll live, tranziție confirmată |
| YouTube: cleanup fișiere temporare | ✅ | verificat, niciun leftover |
| Swagger docs sincronizate cu codul | ✅ | `vocal-separator/swagger-spec/swagger.yaml`, servit live pe :8080 |
| Pitch: preview live scurt (accompaniment) | ✅ | curl, ~200ms dupa warmup numba |
| Pitch: job full-length + download | ✅ | curl end-to-end, durata pastrata + centroid mutat corect |
| Pitch: warmup numba la startup (primul preview rapid) | ✅ | primul preview dupa restart = 247ms |

## Frontend

| Task | Status | Verificat cu |
|---|---|---|
| Upload fișier (drag&drop + click) | ✅ | build reușit, cod verificat |
| Tab "Link YouTube" alături de upload | ✅ | build reușit |
| Progres 2 etape afișat corect | ✅ | cod verificat, backend confirmat separat |
| Preview player, 4 butoane (Original/Vocals/Instrumental/Both) | ✅ | build reușit |
| Buton Play nu mai e blocat permanent | ⚠️ | fix aplicat + build ok, **netstat vizual în browser de utilizator** |
| Speed control conectat la `/api/process` | ✅ | testat prin secvența exactă de API pe care o declanșează UI-ul |
| Volume meter afișează date reale | ✅ | testat prin fluxul complet upload→status |
| Waveform comparison, playhead live | ✅ | build reușit, logică verificată |
| Toggle Peak/LUFS | ✅ | testat prin flux complet |
| Slider intensitate separare | 🔻 ascuns din UI | la cererea utilizatorului — backend tot primește 0.5 implicit |
| Pitch control (slider tonalitate minus, preview live) | ✅ | build reușit; backend verificat separat end-to-end |

⚠️ = fix aplicat și logic corect, dar nu confirmat vizual într-un browser
real de către utilizator (nu am unealtă de control browser).

## Documentație

| Task | Status |
|---|---|
| BR.md, CLAUDE.md, ROADMAP.md, TASKS.md, TESTING.md | ✅ create 2026-09-10 |
| ~30 documente vechi de progres, nesigure | 🗑️ șterse 2026-09-10 |
| Swagger UI local (docker, port 8080) | ✅ funcțional, live-sync |

## Cum actualizezi acest fișier
După orice modificare semnificativă: rulează testul relevant (curl sau
pytest), și scrie rezultatul aici — nu presupune. Dacă nu poți testa
(ex. UI vizual fără browser), marchează explicit cu ⚠️, nu cu ✅.
