# status – Changelog

## 2026-10-23 – Lokal mit Repo abgeglichen, CLAUDE.md auf HauServer umgestellt

- Lokal mit `origin/main` verglichen: Lokal war 21 Commits hinter dem Remote und hatte keine eigenen Commits. Dazu kamen 3 Änderungen, die nicht committet waren.
- Die lokalen Änderungen an `status.ini` (UNC-Pfade `\\HauServer\...`) und `Setup-TaskScheduler-Fixed.ps1` (ServiceAccount `HauServer\Service`) verworfen. Der Remote hat beides schon anders gelöst: In `status.ini` stehen lokale `D:\`-Pfade, und das Setup-Skript ist gelöscht.
- Die Änderung an `Status 20250901.docx` verworfen.
- `git pull --ff-only`: alle 21 Commits übernommen, ohne Konflikte.
- `CLAUDE.md`: Den Pfad zur Standardbibliothek und den Service-User im Task-Scheduler-Beispiel auf `HauServer` umgestellt. Die Excel-Quellen `Instrumente.xlsx` und `bookings.xlsx` haben jetzt dieselben `D:\Dataserver\Dummy\Finance_Input\...`-Pfade wie `status.ini`. Committet und gepusht (`d807ed5`).

Verworfene Ansätze:
- Lokale Änderungen per `git stash` aufheben: nicht nötig, weil der Remote dieselben Punkte schon gelöst hatte.
- Excel-Quellen in `CLAUDE.md` als `\\HauServer\...`: Stattdessen die `D:\`-Pfade genommen, damit die Doku zu `status.ini` passt.
