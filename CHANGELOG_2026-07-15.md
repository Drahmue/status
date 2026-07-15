# Changelog - 2026-07-15

## Zusammenfassung

Server wurde von Windows Server 2022 auf Windows Server 2025 neu aufgesetzt, alle Task-Scheduler-Aufgaben wurden neu angelegt. Dabei traten zwei neue Probleme auf, die diagnostiziert und behoben wurden: ein NTFS-Berechtigungsproblem, das `status.py` unter dem Service-Account scheitern ließ, sowie fehlende SSH-Zugangsdaten für Git-Push vom Server aus.

## Kontext

Nach dem Neuaufsetzen des Servers (WS2022 → WS2025) und der Neuanlage aller Aufgaben im Task Scheduler meldete `status.py` beim Start via Task Scheduler:

```
RuntimeError: [Errno 13] Permission denied: '\\HauServer\Dataserver\Dummy\Finance_Input\Instrumente.xlsx'
```

Bekannte Fakten zu Beginn der Diagnose:
- Manuell als Administrator (lokaler Pfad `D:\` als Working Dir) → funktioniert
- Task Scheduler als Service-Account (UNC-Pfad `\\HauServer\` als Working Dir) → Fehler
- NTFS: Service hatte `(I)(OI)(CI)(RX)` auf `Dummy\Finance_Input`
- `DisableLoopbackCheck=1` und `BackConnectionHostNames=HauServer` waren bereits gesetzt
- SMB-Share: Administratoren-Gruppe war bereits hinzugefügt

## Problem 1: NTFS-Berechtigung unzureichend für Lock-Check

### Root Cause

`is_file_open_windows()` in `ahlib.py` (`.venv\Lib\site-packages\ahlib\ahlib.py`, Zeile ~498, aufgerufen aus `files_availability_check()`) öffnet die zu prüfende Datei im Schreibmodus, um testweise eine Sperre zu setzen:

```python
with open(file_path, 'r+b') as file:
    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
```

`'r+b'` erfordert NTFS-**Schreibrecht** (Modify), obwohl die Datei inhaltlich nie verändert wird. Reines Leserecht (Read & Execute) reicht nicht aus. Der Service-Account hatte nach dem Server-Neuaufsetzen nur `(RX)` statt `(M)` auf `Finance_Input` – die neu vergebenen ACLs entsprachen nicht dem in DEPLOYMENT.md dokumentierten Minimum.

### Ausgeschlossene Ursachen (False Leads)

- **`DisableLoopbackCheck` / `BackConnectionHostNames`**: Diese Registry-Einstellungen betreffen ausschließlich NTLM-Loopback-Authentifizierung für **IIS/HTTP**-Anwendungen. Sie haben keinerlei Wirkung auf SMB-Dateizugriffe. Sie können gesetzt bleiben, waren aber nie die Ursache dieses Problems.
- **SMB-Share-Berechtigungen**: `Get-SmbShareAccess -Name Dataserver` zeigte bereits `HAUSERVER\Service: Change` – ausreichend. Windows wendet bei kombinierten Share-/NTFS-Rechten das jeweils restriktivere an; die NTFS-Ebene war der alleinige Flaschenhals.

### Diagnose

```powershell
icacls "D:\Dataserver\Dummy\Finance_Input"
icacls "D:\Dataserver\Dummy\Finance_Input\Instrumente.xlsx"
# Ergebnis vor Fix: HAUSERVER\Service:(I)(RX)  ← Problem
```

### Fix

```powershell
icacls "D:\Dataserver\Dummy\Finance_Input" /grant "HAUSERVER\Service:(OI)(CI)M" /T
```

Ergebnis nach Fix:
```
HAUSERVER\Service:(I)(M)
```

### Verifikation

Task manuell gestartet, Log geprüft — Fehler tritt nicht mehr auf, vollständige Initialisierung erfolgreich:

```
[2026-07-15 16:22:19] Running as user: Service
[2026-07-15 16:22:30] INFO: Datei '\\HauServer\Dataserver\Dummy\Finance_Input\Instrumente.xlsx' ist verfügbar.
[2026-07-15 16:22:30] INFO: Verfügbarkeitscheck abgeschlossen: 2/2 Dateien verfügbar.
[2026-07-15 16:22:30] INFO: Positionen (shares) auf Tagesbasis erfolgreich aufgebaut
```

Zusätzlich wurden alle vier Task-Scheduler-Aufgaben (`Stock Monitoring Service`, `Status Web App`, `DSL Speedtest Monitoring`, `Zaehler Monitoring`) einzeln verifiziert: Alle laufen unter dem `Service`-Account (`Running as user: Service` in den jeweiligen Logs), alle Ausgabedateien (`depotdaten.json`, `speedtest.json`, `zaehler.json`) werden aktuell aktualisiert, Web-Dashboard antwortet mit HTTP 200.

Ebenfalls geprüft: `ExecutionTimeLimit` aller vier Daemon-Tasks steht korrekt auf `PT0S` (kein Zeitlimit) — der frühere 72h-Auto-Stop-Bug (siehe CHANGELOG_2026-02-27.md) ist trotz Neuanlage der Tasks nicht wieder aufgetreten.

## Problem 2: Fehlender SSH-Zugriff für Git-Push vom Server

### Symptom

```
git push origin main
# Host key verification failed. / Permission denied (publickey).
```

### Root Cause

Nach dem Neuaufsetzen war `%USERPROFILE%\.ssh` leer – weder GitHub-Host-Key in `known_hosts` noch ein Schlüsselpaar für die Authentifizierung vorhanden.

### Fix

```powershell
# 1. GitHub-Host-Key hinzufügen
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> $env:USERPROFILE\.ssh\known_hosts

# 2. Neues Schlüsselpaar erzeugen
ssh-keygen -t ed25519 -C "member@haunschild-family.de" -f $env:USERPROFILE\.ssh\id_ed25519 -N '""'

# 3. Public Key als Deploy Key im Repo Drahmue/status hinterlegt (mit "Allow write access")
```

Zusätzlich musste die lokale Git-Identität (`user.name`, `user.email`) neu gesetzt werden, da diese nach dem Neuaufsetzen ebenfalls fehlte (`git config --global user.name "Drahmue"`, `user.email "member@haunschild-family.de"`).

### Verifikation

`git push origin main` erfolgreich (`ae916f0..a19b479  main -> main`).

## Geänderte/Neue Dateien

- **NEU:** `CHANGELOG_2026-07-15.md` (dieses Dokument)
- **GEÄNDERT:** `TROUBLESHOOTING_STOCK_MONITORING.md` – neuer Abschnitt "Permission denied trotz lesbarer Datei (Errno 13)"
- **GEÄNDERT:** `CLAUDE.md` – neuer Eintrag "NTFS Permission Bug After Server Rebuild" unter "Known Issues and Fixes"
- **GEÄNDERT:** `DEPLOYMENT.md` – Warnhinweis zu Modify-Rechten (§1.6/§2.1), neuer Abschnitt "SSH Key for GitHub Access" (§1.1), Version auf 2.1 angehoben
- **GEÄNDERT:** `CHANGELOG.md` (Master) – Eintrag in Changelog-Übersicht ergänzt

## Lessons Learned

1. **Bei jedem Server-/Account-Neuaufsetzen NTFS-ACLs explizit mit `icacls` verifizieren**, nicht nur SMB-Share-Berechtigungen – Windows vergibt diese unabhängig voneinander, und "Read & Execute" reicht für Skripte, die Lock-Checks via Schreibmodus durchführen, nicht aus.
2. **IIS-Loopback-Einstellungen (`DisableLoopbackCheck`, `BackConnectionHostNames`) sind kein Diagnose-Ansatz für SMB-Probleme** – sie betreffen ausschließlich HTTP/NTLM, nicht Dateifreigaben.
3. **SSH-Schlüssel und Git-Identität gehören zur Server-Neuaufsetzen-Checkliste**, wenn der Server selbst Commits pushen soll (bisher nur implizit vorausgesetzt, nicht dokumentiert).
4. **`ExecutionTimeLimit=PT0S` sollte nach jeder Task-Neuanlage stichprobenartig geprüft werden**, auch wenn es dieses Mal korrekt übernommen wurde.

## Referenzen

- **Verwandte Dokumente:** `TROUBLESHOOTING_STOCK_MONITORING.md`, `CLAUDE.md`, `DEPLOYMENT.md`
- **Vorheriges kritisches Changelog:** `CHANGELOG_2026-02-27.md` (ExecutionTimeLimit-Bug, Silent Crash)
