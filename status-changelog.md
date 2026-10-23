# status – Changelog

## 2026-10-23 – Lokal mit Repo abgeglichen, CLAUDE.md auf HauServer umgestellt

- Lokal mit `origin/main` verglichen: Lokal war 21 Commits hinter dem Remote und hatte keine eigenen Commits. Dazu kamen 3 Änderungen, die nicht committet waren.
- Die lokalen Änderungen an `status.ini` (UNC-Pfade `\\HauServer\...`) und `Setup-TaskScheduler-Fixed.ps1` (ServiceAccount `HauServer\Service`) verworfen. Der Remote hat beides schon anders gelöst: In `status.ini` stehen lokale `D:\`-Pfade, und das Setup-Skript ist gelöscht.
- Die Änderung an `Status 20250901.docx` verworfen.
- `git pull --ff-only`: alle 21 Commits übernommen, ohne Konflikte.
- `CLAUDE.md`: Den Pfad zur Standardbibliothek und den Service-User im Task-Scheduler-Beispiel auf `HauServer` umgestellt. Die Excel-Quellen `Instrumente.xlsx` und `bookings.xlsx` haben jetzt dieselben `D:\Dataserver\Dummy\Finance_Input\...`-Pfade wie `status.ini`. Committet und gepusht (`d807ed5`).

- ST-01 erledigt: In `DEPLOYMENT.md`, `TROUBLESHOOTING_STOCK_MONITORING.md`, `startscript_fehlermeldung_status.md` und `CHANGELOG.md` steht jetzt `HauServer` statt `WIN-H7BKO5H0RMC`. Pfade auf `\\WIN-H7BKO5H0RMC\Dataserver` sind jetzt lokale `D:\Dataserver`-Pfade, so wie in den Start-Skripten. Die Standardbibliothek und der UNC-Hinweis verweisen auf `\\HauServer\...`. Den veralteten Abschnitt zu `$scriptDir` in `startscript_fehlermeldung_status.md` habe ich als „überholt“ markiert, weil die Skripte inzwischen `$PSScriptRoot` verwenden.

Verworfene Ansätze:
- Lokale Änderungen per `git stash` aufheben: nicht nötig, weil der Remote dieselben Punkte schon gelöst hatte.
- Excel-Quellen in `CLAUDE.md` als `\\HauServer\...`: Stattdessen die `D:\`-Pfade genommen, damit die Doku zu `status.ini` passt.
