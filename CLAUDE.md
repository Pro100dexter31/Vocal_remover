# CLAUDE.md

Instrucțiuni pentru Claude Code când lucrează în acest repo.

## Ce este proiectul
Vocal Separator: upload fișier audio sau link YouTube → separare AI
(vocals/instrumental via Demucs) → preview, ajustare volum/viteză →
download. Detalii complete de business în [BR.md](BR.md), roadmap în
[ROADMAP.md](ROADMAP.md).

## Stack tehnic
- **Backend**: FastAPI + Celery (Redis broker) + Demucs (PyTorch, CPU) —
  `vocal-separator/backend/`
- **Frontend**: React (Create React App) + Tailwind — `vocal-separator/frontend/`
- **Infra**: Docker Compose (5 servicii: backend, celery, frontend, redis,
  swagger-ui) — `vocal-separator/docker-compose.yml`

## Cum rulezi local
```bash
cd vocal-separator
docker compose up -d          # tot stack-ul
docker compose build <serviciu>  # rebuild dupa modificare cod
```
Sau folosește `./do.sh` din root (vezi secțiunea Helpers mai jos).

| Serviciu | Port | Ce e |
|---|---|---|
| backend | 8000 | API FastAPI |
| frontend | 3001 | UI React |
| swagger-ui | 8080 | Docs API interactive, live-sync cu `vocal-separator/swagger-spec/swagger.yaml` |
| redis | 6379 | Broker Celery |

**Important**: `backend` și `celery` rulează din **aceeași imagine Docker**
(`backend/Dockerfile`). Orice modificare de cod backend necesită
`docker compose build backend celery && docker compose up -d backend celery`
— cod nou NU apare doar cu `up -d`, imaginea trebuie reconstruită.

## Rulare teste
```bash
docker exec vocal_remover-backend-1 python3 -m pytest backend/ -v
```
`pytest`/`pytest-mock` sunt incluse permanent în imagine (`requirements-dev.txt`,
instalate în `Dockerfile`) — nu necesită instalare ad-hoc.
118 teste, toate treceau la ultima verificare. Detalii în [TESTING.md](TESTING.md).

## Convenții de cod
- **Backend Python**: indentare cu **tab**, nu spații (verifică fișierele
  existente înainte de a edita — `tasks.py`, `main.py` etc. folosesc tab)
- **Module dedicate per responsabilitate**: `speed_adjuster.py`,
  `volume_normalizer.py`, `audio_converter.py`, `waveform.py`,
  `youtube_extractor.py` — fiecare cu propriile excepții custom, nu
  excepții generice
- **Logică de separare/normalizare/viteză partajată** între upload și
  YouTube prin `_run_separation_pipeline()` în `tasks.py` — nu duplica
  logica dacă adaugi o a treia sursă de input

## Capcane descoperite (nu le repeta)
- **FastAPI + `UploadFile`**: orice alt parametru din body trebuie
  `= Form(...)` explicit, altfel FastAPI îl tratează ca query param și îl
  ignoră silențios din multipart form-data. A fost un bug real, prezent
  luni de zile nedetectat.
- **`soundfile` nu poate scrie MP3 direct** — `adjust_speed()` scrie doar
  WAV/FLAC/OGG. Pentru MP3, treci printr-un WAV temporar +
  `audio_converter.convert_audio()`. Vezi helper `_stretch_to_matching_format()`.
- **Numba (via librosa) are nevoie de `NUMBA_CACHE_DIR` scriabil** în
  container (userul `app` nu are drepturi de scriere în `site-packages`).
  Deja setat în `docker-compose.yml`.
- **yt-dlp are nevoie de un runtime JS** (deno) pentru provocările de
  semnătură YouTube — fără el, erori înșelătoare de tip "video unavailable".
  Deja instalat în `backend/Dockerfile`.
- **Mount de fișier unic pe Docker Desktop Mac se rupe** la orice editare
  atomică (rename) a fișierului sursă de pe host. Pentru `swagger.yaml`,
  soluția a fost mount de **director** (`vocal-separator/swagger-spec/`),
  nu de fișier individual. Aplică același pattern dacă mai apare nevoia.
- **Celery task-uri cu callback de progres**: `self.update_state()` merge
  DOAR din thread-ul principal al task-ului. Dacă un callback rulează
  într-un `ThreadPoolExecutor` worker (ex. progres de download yt-dlp),
  scrie într-un holder shared și fă polling din thread-ul principal — vezi
  `process_youtube_task` în `tasks.py`.

## Documentație vie (nu re-crea documente de progres)
Nu mai crea fișiere `FEATURE_X_COMPLETE_SUMMARY.md` sau similare — au fost
șterse deliberat pentru că acumulau afirmații "✅ done" nereale, nevalidate
niciodată prin rulare efectivă. Actualizează în schimb:
- [ROADMAP.md](ROADMAP.md) pentru ce e planificat
- [TASKS.md](TASKS.md) pentru starea curentă, verificată
- [TESTING.md](TESTING.md) pentru acoperirea de teste

Orice afirmație de tip "funcționează" trebuie verificată prin rulare
reală (curl, pytest, sau test manual în browser) înainte de a fi scrisă
ca fapt — acest proiect are un istoric de documentație care pretindea
funcționalitate ce nu exista.
