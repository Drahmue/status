# Troubleshooting: Stock Monitoring Service

Dieses Dokument beschreibt, wie Sie den Stock Monitoring Service diagnostizieren, wenn er nicht läuft.

## Problem-Beschreibung

Der Stock Monitoring Service ist ein **Daemon-Prozess**, der:
- Beim Systemstart automatisch starten soll (Boot-Trigger in Task Scheduler)
- Dauerhaft im Hintergrund läuft
- Alle 60 Sekunden Aktienkurse aktualisiert
- Um Mitternacht prüft, ob ein neuer Handelstag begonnen hat

**Bekannte Probleme – alle behoben:**

**Problem 1: Task Scheduler ExecutionTimeLimit PT72H (Hauptursache, Februar 2026)**
- Service stoppte nach exakt 72 Stunden ohne Log-Eintrag
- Exit Code 267014 = Task durch ExecutionTimeLimit beendet
- Betraf alle drei Daemon-Tasks (Nov 2025, Feb 2026 mehrfach)
- **Behoben:** ExecutionTimeLimit auf PT0S gesetzt (kein Limit)

**Problem 2: Fehlende Fehlerbehandlung in run_monitor() (sekundär, Februar 2026)**
- Unbehandelte Exceptions in der `while True`-Schleife beendeten das Script lautlos
- Kein Fehler-Log, kein Traceback
- **Behoben:** Äußerer try/except-Block mit vollem Traceback-Logging ergänzt

**Problem 3: NTFS-Rechte nach Server-Neuaufsetzen unvollständig (Juli 2026)**
- Nach Neuaufsetzen des Servers (WS2022 → WS2025) `RuntimeError: [Errno 13] Permission denied` beim Zugriff auf `Instrumente.xlsx`
- Ursache: Service-Account hatte nur Read & Execute statt Modify auf `Finance_Input`
- **Behoben:** NTFS-Modify-Recht für Service-Account ergänzt (siehe Abschnitt "Problem: Permission denied trotz lesbarer Datei (Errno 13)")

## Diagnose-Schritte

### 1. Task Scheduler Status prüfen

```powershell
# Task-Status anzeigen
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object TaskName, State, LastRunTime, LastTaskResult | Format-List

# Detaillierte Informationen
Get-ScheduledTaskInfo -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns | Format-List
```

**Erwartete Werte:**
- `State: Running` - Service läuft
- `State: Ready` - Service läuft NICHT (Problem!)
- `LastTaskResult: 267009` (0x41301) - Task läuft aktuell (gut)
- `LastTaskResult: 267014` (0x41306) - Task wurde beendet (Problem!)
- `LastTaskResult: 0` - Task erfolgreich beendet (sollte nicht vorkommen bei Daemon!)

### 2. PowerShell Starter-Script Logs prüfen

**Log-Verzeichnis:** `D:\Dataserver\_Batchprozesse\status\logs\`

```powershell
# Aktuelles Monats-Log anzeigen
$month = Get-Date -Format "yyyy-MM"
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_$month.log" -Tail 50

# Nach spezifischem Datum suchen
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_$month.log" | Select-String -Pattern "2025-12-03" -Context 5,10

# Fehler-Log prüfen (falls vorhanden)
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_errors_$month.log" -Tail 50
```

**Was zu suchen:**
- `Starting Stock Monitoring Service` - Script wurde gestartet
- `Network share ... is available` - Netzwerk verfügbar
- `Changed directory to: ...` - Arbeitsverzeichnis gewechselt
- `Starting Python script...` - Python wurde gestartet
- Fehlermeldungen über Netzwerk-Timeout (max. 5 Minuten Wait-Zeit)

### 3. Python-Script Logs prüfen

**Log-Datei:** `D:\Dataserver\_Batchprozesse\status\status.log`

```powershell
# Letzte 100 Zeilen anzeigen
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 100

# Nach spezifischem Datum suchen
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" | Select-String -Pattern "2025-12-03" -Context 5,10

# Letzte Initialisierung finden
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" | Select-String -Pattern "Logger erfolgreich initialisiert" -Context 0,10 | Select-Object -Last 1

# Letzte Referenzdaten-Aktualisierung finden
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" | Select-String -Pattern "Referenzdaten.*aktualisiert" | Select-Object -Last 5
```

**Normale Log-Sequenz beim Start:**
1. `Logger erfolgreich initialisiert mit Logfile: status.log`
2. `Arbeitsverzeichnis wurde auf das Verzeichnis des Callers gesetzt`
3. `Arbeitsverzeichnis erfolgreich gesetzt`
4. `Datei '...\Instrumente.xlsx' ist verfügbar`
5. `Datei '...\bookings.xlsx' ist verfügbar`
6. `Verfügbarkeitscheck abgeschlossen: 2/2 Dateien verfügbar`
7. `Alle Dateien verfügbar und erfolgreich geladen`
8. `Initialisierung erfolgreich abgeschlossen`
9. `Instruments-Datei erfolgreich geladen`
10. `Alle WKNs aus Buchungen sind in Instruments vorhanden`
11. `Buchungen-Import und -Verarbeitung erfolgreich abgeschlossen`
12. `Positionen (shares) auf Tagesbasis erfolgreich aufgebaut`

**Tägliche Updates (um Mitternacht):**
- `[YYYY-MM-DD 00:00:XX] INFO: Referenzdaten für neuen Handelstag DD.MM.YYYY aktualisiert`

**Fehlermeldungen:**
- `ERROR: ...` - Schwerwiegende Fehler
- `WARNING: Keine Shares-Daten für neuen Handelstag` - Daten noch nicht verfügbar
- `ERROR: WKNs aus Buchungen fehlen in Instruments` - Datenfehler

### 4. Windows Event Log prüfen

```powershell
# Task Scheduler Events für Stock Monitoring Service
$startTime = Get-Date "2025-12-03 00:00:00"  # Anpassen!
$endTime = Get-Date "2025-12-03 23:59:59"    # Anpassen!

Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-TaskScheduler/Operational'
    StartTime=$startTime
    EndTime=$endTime
} -MaxEvents 1000 -ErrorAction SilentlyContinue |
Where-Object { $_.Message -like '*Stock Monitoring*' } |
Select-Object TimeCreated, Id, LevelDisplayName, Message |
Format-List
```

**Wichtige Event IDs:**
- **118** - Boot-Trigger aktiviert
- **100** - Task-Instanz gestartet
- **129** - Prozess gestartet (mit Prozess-ID)
- **200** - Aktion gestartet
- **201** - Task erfolgreich abgeschlossen (mit Exit Code)
- **102** - Task-Instanz erfolgreich beendet

### 5. Prozess-Status prüfen

```powershell
# Python-Prozesse anzeigen, die status.py ausführen
Get-Process python* -ErrorAction SilentlyContinue |
Where-Object { $_.CommandLine -like '*status.py*' } |
Select-Object Id, ProcessName, StartTime, CPU, WorkingSet

# Alle PowerShell-Prozesse von Service-User
Get-Process powershell* -ErrorAction SilentlyContinue |
Where-Object { $_.UserName -like '*Service*' } |
Select-Object Id, ProcessName, StartTime, CPU, WorkingSet
```

## Häufige Probleme und Lösungen

### Problem: Service läuft nicht nach Boot

**Symptome:**
- Task Scheduler zeigt `State: Ready` statt `Running`
- Keine neuen Einträge in Logs seit letztem Boot

**Diagnose:**
1. Prüfen Sie Event Log für Boot-Trigger (Event ID 118)
2. Prüfen Sie PowerShell-Logs für Netzwerk-Timeout
3. Prüfen Sie Python-Logs für Initialisierungsfehler

**Lösungen:**
- **Netzwerk zu langsam**: Boot-Trigger mit 2-3 Minuten Verzögerung konfigurieren
- **Netzwerk-Timeout**: `$MAX_NETWORK_WAIT` in `start_status.ps1` erhöhen (Zeile 23)
- **Manueller Start**: `Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"`

### Problem: Service stoppt unerwartet nach ~72 Stunden ✅ BEHOBEN

**Symptome:**
- Service lief, stoppte aber nach exakt ~72 Stunden ohne Fehler-Log
- Exit Code 267014 in Task Scheduler
- Letztes JSON-Update exakt 72h nach dem letzten Task-Start

**Ursache:** Task Scheduler `ExecutionTimeLimit = PT72H` (Standard-Wert wenn nicht explizit gesetzt)

**Diagnose:**
```powershell
# Execution Time Limit prüfen
$task = Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
$task.Settings.ExecutionTimeLimit
# Ergebnis "PT72H" = Problem, "PT0S" = kein Limit (korrekt)

# Laufzeit des letzten Starts berechnen
$start = (Get-ScheduledTaskInfo -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\").LastRunTime
$lastJson = (Get-Content "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | ConvertFrom-Json).price_timestamp
Write-Output "Laufzeit: $(([datetime]$lastJson - $start).TotalHours) Stunden"
```

**Lösung (bereits angewendet):**
```powershell
$task = Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
$task.Settings.ExecutionTimeLimit = "PT0S"
$pw = Read-Host "Passwort für Service-Account" -AsSecureString
$pwPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))
Set-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Settings $task.Settings -User "WIN-H7BKO5H0RMC\Service" -Password $pwPlain
```

**Hinweis:** DSL Speedtest Monitoring und Status Web App hatten bereits `PT0S`, waren nicht betroffen.

### Problem: Netzwerk-Dateien nicht verfügbar

**Symptome:**
- `ERROR: Eine oder mehrere Dateien fehlen` in Logs
- `Waiting for network share to be available` in PowerShell-Logs

**Diagnose:**
```powershell
# Netzwerk-Verfügbarkeit testen
Test-Path "\\WIN-H7BKO5H0RMC\Dataserver"
Test-Path "\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx"
Test-Path "\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx"
```

**Lösungen:**
- Netzwerkverbindung prüfen
- Berechtigungen für Service-User prüfen
- Firewall-Einstellungen prüfen

### Problem: Permission denied trotz lesbarer Datei (Errno 13) ✅ BEHOBEN (Juli 2026)

**Symptome:**
```
RuntimeError: [Errno 13] Permission denied: '\\HauServer\Dataserver\Dummy\Finance_Input\Instrumente.xlsx'
```
- Fehler tritt in `ahlib.py`, Funktion `is_file_open_windows()` auf
- Manuell als Administrator (lokaler Pfad `D:\...` als Working Dir) funktioniert der Zugriff
- Als Service-Account über Task Scheduler (UNC-Pfad `\\HauServer\...` als Working Dir) schlägt er fehl
- `Test-Path` auf die Datei liefert `True` – die Datei ist grundsätzlich sichtbar/lesbar

**Typischer Auslöser:** Server-Neuaufsetzen (z. B. WS2022 → WS2025) oder Neuanlage des Service-Accounts – NTFS-ACLs werden dabei nicht automatisch migriert bzw. nur mit den in DEPLOYMENT.md als "Minimum" genannten Rechten neu vergeben.

**Root Cause:**
`is_file_open_windows()` in `ahlib.py` (Zeile ~498) prüft, ob eine Datei gesperrt ist, indem es sie **schreibend** öffnet:
```python
with open(file_path, 'r+b') as file:
    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
```
`'r+b'` erfordert NTFS-Schreibrecht – reines Leserecht (Read & Execute) reicht nicht, obwohl die Datei nie tatsächlich verändert wird. Das ist unabhängig vom lokalen/UNC-Pfad; der Unterschied "Administrator funktioniert, Service-Account nicht" kommt daher, dass Administrator vollen Zugriff (F) hat, der Service-Account aber nur RX.

**Wichtig – False Leads, die NICHT die Ursache sind:**
- `DisableLoopbackCheck` / `BackConnectionHostNames`: Das sind **IIS/HTTP-NTLM-Mechanismen**, die den Loopback-Zugriff auf Webanwendungen betreffen. Sie haben **keinen Effekt auf SMB-Dateizugriffe**. Diese Registry-Einstellungen können gesetzt bleiben (schaden nicht), lösen dieses Problem aber nicht.
- SMB-Share-Berechtigungen (`Get-SmbShareAccess`): Waren im beobachteten Fall bereits korrekt (`Change` für den Service-Account). Windows kombiniert Share- und NTFS-Rechte und wendet das restriktivere an – die NTFS-Ebene war der Flaschenhals, nicht die Freigabe-Ebene.

**Diagnose:**
```powershell
# NTFS-Rechte des Service-Accounts auf Ordner und Datei prüfen
icacls "D:\Dataserver\Dummy\Finance_Input"
icacls "D:\Dataserver\Dummy\Finance_Input\Instrumente.xlsx"
# Wenn nur "(RX)" statt "(M)" oder "(F)" für den Service-Account erscheint: das ist die Ursache

# Zum Vergleich: SMB-Share-Ebene prüfen (meist NICHT die Ursache)
Get-SmbShareAccess -Name Dataserver
```

**Lösung:**
```powershell
# Modify-Recht rekursiv für den Service-Account ergänzen (additiv, entfernt nichts Bestehendes)
icacls "D:\Dataserver\Dummy\Finance_Input" /grant "HAUSERVER\Service:(OI)(CI)M" /T
```
Danach Task neu starten und `status.log` prüfen – die Zeile `Verfügbarkeitscheck abgeschlossen: 2/2 Dateien verfügbar.` muss ohne nachfolgenden `RuntimeError` erscheinen.

**Hinweis für zukünftige Server-Neuaufsetzen:** DEPLOYMENT.md §2.1 nennt "Read & execute, Write, Modify" als Minimum – bei ACL-Neuvergabe nach einem Server-Wechsel darauf achten, dass tatsächlich **Modify** (nicht nur Read & Execute) gesetzt wird, da `is_file_open_windows()` dies zwingend benötigt.

## Service manuell starten

```powershell
# Task manuell starten
Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"

# Status nach 30 Sekunden prüfen
Start-Sleep -Seconds 30
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object State

# Logs prüfen
$month = Get-Date -Format "yyyy-MM"
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_$month.log" -Tail 20
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 20
```

## Service stoppen

```powershell
# Task stoppen (stoppt den PowerShell-Prozess, aber nicht unbedingt Python!)
Stop-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"

# Python-Prozess direkt stoppen (falls Task-Stop nicht funktioniert)
Get-Process python* | Where-Object { $_.CommandLine -like '*status.py*' } | Stop-Process -Force
```

## Monitoring-Script für automatischen Restart

**Zukünftige Verbesserung:** Ein separater Monitoring-Task könnte regelmäßig prüfen, ob der Service läuft, und ihn automatisch neu starten wenn nötig.

```powershell
# Beispiel: Service-Health-Check
$task = Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
if ($task.State -ne "Running") {
    Write-Output "[$(Get-Date)] WARNING: Stock Monitoring Service ist nicht aktiv. Starte neu..."
    Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
}
```

## Log-Dateien Übersicht

| **Datei** | **Typ** | **Inhalt** | **Rotation** |
|-----------|---------|------------|--------------|
| `logs\status_YYYY-MM.log` | PowerShell Starter | Script-Start, Netzwerk-Wait, Python-Start | Monatlich |
| `logs\status_errors_YYYY-MM.log` | PowerShell Errors | Starter-Script Fehler | Monatlich |
| `status.log` | Python Script | Initialisierung, Datenverarbeitung, Updates | Keine (wächst kontinuierlich) |
| `temp_init.log` | Temporär | Initialisierung (wird gelöscht) | Einmalig |

**Log-Cleanup:** PowerShell-Logs älter als 120 Tage werden automatisch gelöscht.

## Wichtige Konfigurationsdateien

| **Datei** | **Zweck** |
|-----------|-----------|
| `start_status.ps1` | PowerShell Starter-Script mit Netzwerk-Wait-Logik |
| `status.py` | Python Monitoring-Script (Daemon) |
| `status.ini` | Konfiguration für Python-Script |

**Netzwerk-Wait Konfiguration** (start_status.ps1, Zeile 22-24):
```powershell
$MAX_NETWORK_WAIT = 60         # 60 Versuche
$WAIT_INTERVAL_SECONDS = 5     # je 5 Sekunden = max. 5 Minuten
```

**Refresh-Interval** (status.ini, Zeile 23):
```ini
refresh_time = 60  # Sekunden zwischen Updates
```

## Analyse-Historie

**Erste Analyse:** 03.12.2025
- Boot am 25.11.2025 20:22 - Service startete erfolgreich nach 2 Minuten Netzwerk-Wait
- Service lief korrekt vom 25.11. bis 28.11. (~72h) – Ursache noch unklar
- Exit Code 267014

**Zweite Analyse:** 27.02.2026 – **Ursache identifiziert und behoben**
- Muster entdeckt: Service stoppte immer nach exakt ~72h (Nov 2025, Feb 2026 zweimal)
- Ursache 1: Task Scheduler `ExecutionTimeLimit = PT72H` → auf `PT0S` gesetzt
- Ursache 2: Fehlende try/except in `run_monitor()` → äußerer try/except ergänzt
- Beide Fixes in status.py und Task Scheduler angewendet

---

## Schnell-Checkliste

Wenn der Service nicht läuft:

- [ ] Task Scheduler Status: `Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"`
- [ ] PowerShell Log: `Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_$(Get-Date -Format 'yyyy-MM').log" -Tail 50`
- [ ] Python Log: `Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 100`
- [ ] Letzte Referenzdaten-Aktualisierung: `Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" | Select-String "Referenzdaten.*aktualisiert" | Select-Object -Last 1`
- [ ] Event Log: Siehe Abschnitt 4
- [ ] Manueller Start: `Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"`
