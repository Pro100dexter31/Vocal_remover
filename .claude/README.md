# .claude/ — referințe pentru Claude Code

Acest folder conține documentele de context/planificare pe care le
citește Claude Code, separate de codul propriu-zis.

| Fișier | Ce conține |
|---|---|
| `vocal-separator-features-1-6-prompt.md` | Prompt-ul original cu Feature 1-6 (slider separare, export formate, normalizare volum, preview live, speed control, waveform comparison) — task-uri detaliate, checkbox-uri |
| `vocal-separator-feature-7-youtube-prompt.md` | Prompt Feature 7 (YouTube → minus) — decizii tehnice deja luate (limită 15 min, 320kbps, progres pe 2 etape) |
| `settings.local.json` | Permisiuni locale Claude Code pentru acest proiect (necomis în git — vezi `~/.gitignore_global`) |

## Cum se folosește
Aceste fișiere sunt **prompt-uri istorice** de planificare, nu documentație
vie a stării curente. Pentru starea reală, verificată, a proiectului,
vezi în rădăcina repo-ului:
- [`../ROADMAP.md`](../ROADMAP.md) — ce e planificat, pe faze
- [`../TASKS.md`](../TASKS.md) — ce e făcut/verificat acum
- [`../TESTING.md`](../TESTING.md) — acoperire de teste

Dacă adaugi un Feature 8+, urmează același pattern: un fișier
`vocal-separator-feature-N-<nume>-prompt.md` cu task-uri detaliate,
checkbox-uri, și orice decizie tehnică deja luată (ca să nu mai fie
întrebată din nou).
