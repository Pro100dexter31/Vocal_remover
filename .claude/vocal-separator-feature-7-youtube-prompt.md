# 📺 FEATURE 7: YouTube Link → MP3 → Minus (Instrumental)

## Instrucțiuni Generale
Implementează taskurile în ordine. Testează după fiecare task, cu accent pe: calitate audio, consum de memorie/CPU, și eșec grațios pe link-uri invalide/video-uri prea lungi. Raportează blocaje imediat.

## Decizii deja luate (nu mai întreba, doar implementează)
- **Plasare UI**: opțiune nouă alături de upload de fișier — utilizatorul alege între tab-ul "Încarcă fișier" și tab-ul "Link YouTube"; restul fluxului (separare, preview, speed, export) rămâne identic pentru ambele.
- **Limită durată video**: **max 15 minute**. Video-uri mai lungi sunt respinse înainte de a începe download-ul (verificare din metadata, nu după descărcare).
- **Calitate audio extras**: **320 kbps MP3**.
- **Afișare progres**: **2 etape clare și separate** — "1. Descarc audio de pe YouTube... (X%)" urmat de "2. Separ vocea... (X%)" — nu o singură bară unificată.

## Notă legală/etică (de inclus în UI, nu de ignorat)
Descărcarea de conținut YouTube poate încălca Termenii de Serviciu YouTube pentru conținut protejat prin drepturi de autor. Adaugă un text vizibil în UI, lângă câmpul de link: *"Folosește doar cu conținut pentru care ai drepturi (piesele tale, conținut liber de drepturi, sau uz personal permis)."* Nu bloca funcțional feature-ul pe baza asta — doar informează utilizatorul.

---

## Task 7.1: Backend — Validare link + citire metadata (fără download)

- [ ] Instalează `yt-dlp` (fork activ menținut al youtube-dl, mai fiabil) în `requirements.txt`
- [ ] Creează modul nou `youtube_extractor.py` (același pattern ca `speed_adjuster.py`, `audio_converter.py`)
- [ ] Funcție `validate_youtube_url(url: str) -> bool` — acceptă `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`; respinge orice alt domeniu
- [ ] Funcție `fetch_video_metadata(url: str) -> dict` — folosește `yt_dlp.YoutubeDL` cu `download=False` pentru a obține `{title, duration_seconds, uploader}` **fără să descarce nimic**
- [ ] Excepție dedicată `VideoTooLongError` — aruncată dacă `duration_seconds > 900` (15 min), **înainte** de orice download
- [ ] Excepție dedicată `VideoUnavailableError` — pentru video privat/șters/restricționat geografic/age-restricted (mesaj clar pentru fiecare caz, nu generic)
- [ ] Testează manual cu: link valid scurt, link valid >15min (trebuie respins), link invalid/inexistent, link către alt site (ex. Vimeo — trebuie respins)

## Task 7.2: Backend — Extragere audio (download + conversie)

- [ ] Funcție `download_audio(url: str, output_dir: Path) -> Path` — descarcă **doar stream-ul audio** (`format="bestaudio/best"`, NU tot video-ul — economie majoră de bandwidth și memorie)
- [ ] Folosește `ffmpeg` (deja în imaginea Docker) via yt-dlp's `postprocessors` pentru a extrage/converti direct la MP3 320kbps — evită pasul intermediar de a ține tot fișierul audio brut (webm/m4a) pe disk mai mult decât e necesar
- [ ] Descarcă direct pe disk (streaming la scriere), **niciodată în memorie RAM integral** — yt-dlp face asta nativ, verifică doar că nu se dezactivează
- [ ] Șterge fișierul audio intermediar (pre-conversie) imediat după ce conversia la MP3 320kbps reușește
- [ ] Testează cu un video real scurt (<2 min) — verifică: fișierul rezultat e MP3 valid, 320kbps, deschis fără erori în player

## Task 7.3: Backend — Integrare cu pipeline-ul de separare existent

- [ ] Creează task Celery nou `process_youtube_task(self, task_id, url, separation_intensity, normalize, speed, normalization_method)` — orchestrează: fetch metadata → validare durată → download → apoi reutilizează **exact aceeași logică** de separare din `process_audio_task` (nu duplica codul de Demucs/normalizare/speed — extrage partea comună într-o funcție interbă apelabilă din ambele task-uri)
- [ ] Progres pe 2 etape distincte via `self.update_state`:
  - `{"stage": "downloading", "progress": 0-30}` — cât timp descarcă de pe YouTube
  - `{"stage": "separating", "progress": 30-100}` — cât timp separă vocea (identic cu fluxul de upload)
- [ ] După separare, șterge fișierul MP3 descărcat de pe YouTube (aceeași optimizare de disk ca la upload-urile normale)
- [ ] Verifică: waveform data (Feature 6), volume meter (Feature 3), speed adjustment (Feature 5) funcționează identic indiferent dacă sursa a fost upload sau YouTube — pentru că folosesc aceeași logică internă
- [ ] Testează end-to-end: link YouTube → status PROCESSING (downloading) → status PROCESSING (separating) → status SUCCESS → download vocals/accompaniment funcționează

## Task 7.4: Backend — Siguranță memorie/CPU

- [ ] Limitează job-uri YouTube concurente — un singur download YouTube activ per worker Celery la un moment dat (evită saturarea bandwidth-ului/CPU dacă mai mulți utilizatori trimit link-uri simultan)
- [ ] Timeout explicit pe download (ex. 5 minute) — dacă YouTube/rețeaua e lentă, eșuează curat cu mesaj clar, nu blochează worker-ul la infinit
- [ ] Verifică (`docker stats`) consumul de memorie în timpul unui download+separare completă pe un video de 15 minute (limita maximă) — trebuie să rămână în aceeași plajă ca un upload manual de fișier de dimensiune similară
- [ ] Curăță orice fișier temporar (pre-conversie, cache yt-dlp) chiar și pe eșec — folosește `try/finally`, nu doar happy path

## Task 7.5: Backend — API Endpoint

- [ ] Endpoint nou: `POST /api/youtube` — body JSON: `{url, separation_intensity?, normalize?, speed?, normalization_method?}` (aceiași parametri ca `/api/upload`, plus `url` în loc de fișier)
- [ ] Validează `url` cu `validate_youtube_url()` — 400 dacă nu e link YouTube valid
- [ ] Apelează `fetch_video_metadata()` sincron, înainte de a răspunde — dacă durata > 15 min, răspunde imediat cu 400 și mesaj clar ("Video prea lung: X min. Limita: 15 min."), **fără să pornească vreun task Celery**
- [ ] Dacă validarea trece, pornește `process_youtube_task.apply_async(...)`, răspunde 202 cu `task_id` (aceeași formă de răspuns ca `/api/upload`, ca frontend-ul să reutilizeze exact același cod de polling)
- [ ] Documentează endpoint-ul în `swagger.yaml` (tag nou "YouTube"), cu exemple de erori (video prea lung, link invalid, video indisponibil)
- [ ] Testează cu curl: link valid, link prea lung (trebuie 400 imediat, rapid — nu după minute de download), link invalid

## Task 7.6: Frontend — UI pentru link YouTube

- [ ] Adaugă tab-uri/toggle deasupra zonei de upload: **"Încarcă fișier"** | **"Link YouTube"**
- [ ] Tab YouTube: câmp text pentru URL + buton "Extrage și separă" + textul de avertizare legală (vezi secțiunea de mai sus)
- [ ] Validare client-side de bază (regex simplu pentru youtube.com/youtu.be) înainte de a trimite request-ul — feedback instant, nu aștepți round-trip la server pentru un link evident greșit
- [ ] La submit, apelează `POST /api/youtube` (în loc de `/api/upload`), primește `task_id`, pornește polling-ul **exact ca la upload normal** (reutilizează `startPolling`/`checkStatus` existente, fără duplicare de cod)
- [ ] Testează manual: paste link valid, paste link invalid, paste link non-YouTube, paste text random

## Task 7.7: Frontend — Progres pe 2 etape

- [ ] Modifică `StatusResponse`-ul afișat: dacă `status.stage === "downloading"`, arată "Descarc audio de pe YouTube... (X%)"; dacă `stage === "separating"`, arată "Separ vocea... (X%)" — text diferit, aceeași bară de progres vizuală
- [ ] Pentru upload-urile de fișier normale (fără `stage`), păstrează comportamentul actual neschimbat (backward compatible)
- [ ] Testează: urmărește vizual tranziția de la "Descarc..." la "Separ..." pe un link real

## Task 7.8: Testing & Quality Assurance

- [ ] Teste unitare `youtube_extractor.py`: validare URL (valid/invalid/alt-domeniu), parsare metadata mock, respingere corectă pe durată >900s
- [ ] Test integrare: 1 video YouTube real, scurt (<1 min), public, fără restricții — flux complet upload→separare→download
- [ ] Test eroare: video privat/șters (mock sau link real expirat) — verifică mesaj de eroare clar în UI, nu crash
- [ ] Test eroare: video exact la limită (15:01 vs 14:59) — verifică pragul funcționează corect
- [ ] Test memorie: `docker stats` în timpul procesării unui video de 15 minute — documentează consumul (RAM peak) pentru referință viitoare
- [ ] Test calitate: compară audio separat dintr-un video YouTube vs. același audio descărcat manual și încărcat ca fișier — rezultatul separării trebuie să fie identic (confirmă că extracția nu degradează calitatea înainte de separare)
- [ ] Verifică cleanup: după un job YouTube (succes sau eșec), niciun fișier temporar nu rămâne pe disk (`ls` pe folderele de upload/temp)

---

## 🎯 Prioritizare
Implementează Task 7.1 → 7.2 → 7.5 (backend minim funcțional, testabil cu curl) **înainte** de 7.6-7.7 (frontend) — verifică întâi că extracția + separarea funcționează corect izolat, apoi conectezi UI-ul.

## ⚙️ Dependențe noi
- `yt-dlp` (Python package, actualizat frecvent — YouTube își schimbă des structura internă, deci va necesita update-uri periodice ale acestei dependențe)
- `ffmpeg` — deja prezent în imaginea Docker curentă, nu necesită adăugare
