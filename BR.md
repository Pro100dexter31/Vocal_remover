# Business Requirements — Vocal Separator

## Problema
Oamenii vor să extragă vocea sau instrumentalul ("minusul") dintr-o piesă,
fără software scump de studio, fără cont, fără upload pe un site terț
nesigur. Sursele tipice: un fișier audio propriu, sau un link YouTube.

## Utilizatori țintă
- Cântăreți/karaoke: au nevoie de minus pentru practică sau performanță live
- Content creators: extrag acapella sau instrumental pentru remix/cover
- Uz personal: cineva vrea doar să asculte separat vocea unei piese

## Ce trebuie să facă produsul (funcțional)
1. Utilizatorul încarcă un fișier audio **sau** lipește un link YouTube
2. Sistemul separă automat vocea de instrumental (AI, Demucs)
3. Utilizatorul poate asculta rezultatul înainte de a descărca (preview)
4. Utilizatorul poate regla: intensitatea separării, volumul (normalizare),
   viteza de redare
5. Utilizatorul descarcă rezultatul în formatul dorit (MP3/WAV/FLAC/OGG)
6. Utilizatorul poate compara vizual (waveform) originalul vs. vocea vs.
   instrumentalul

## Ce NU trebuie să facă (scop exclus, deliberat)
- Nu ține cont de utilizator / autentificare — e un tool, nu o platformă
- Nu stochează istoric pe termen lung — fișierele se șterg automat (24h,
  configurabil), pentru cost de storage și confidențialitate
- Nu descarcă video de pe YouTube — doar audio (bandwidth, spațiu, și
  pentru că scopul e strict audio)

## Cerințe non-funcționale
- **Calitate**: separare audio de calitate (Demucs `htdemucs`, model
  state-of-the-art), pitch păstrat la ajustările de viteză
- **Cost/resurse**: să ruleze pe hardware modest (CPU, nu GPU obligatoriu),
  memorie sub control (~2GB per job de separare)
- **Legal**: pentru feature-ul YouTube, utilizatorul e responsabil să aibă
  drepturi asupra conținutului — aplicația afișează un avertisment, nu
  blochează funcțional
- **Limite explicite**: fișiere upload max 500MB, video YouTube max 15 min

## Criterii de succes
- Un utilizator nou reușește să separe o piesă și să descarce minusul în
  sub 5 minute, fără documentație externă
- Rezultatul separării e ascultabil, fără artefacte grosolane, pentru
  majoritatea genurilor muzicale populare (pop, rock, hip-hop)
