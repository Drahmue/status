# Troubleshooting: Hanging Script (status.py)

**Erstellt:** 2025-10-23
**Letztes Update:** 2025-10-23
**Problem:** Script läuft, aber aktualisiert JSON nicht mehr

---

## Symptome

- ✗ JSON-Datei (`static/depotdaten.json`) wird seit Stunden nicht mehr aktualisiert
- ✗ Referenzdatum (`reference_date`) ist veraltet/falsch
- ✓ Task "Stock Monitoring Service" zeigt Status "Running"
- ✓ Python-Prozesse laufen (zu sehen in Task Manager)
- ✓ Prozesse verbrauchen sehr wenig CPU (~0.05%)

---

## Schritt-für-Schritt Diagnose

### Schritt 1: Problem bestätigen

**1.1 Aktuelles Datum und erwarteten Handelstag ermitteln:**
```powershell
# Aktuelles Datum
Get-Date -Format "dd.MM.yyyy HH:mm:ss"

# Erwarteter letzter Handelstag (Python)
cd "D:\Dataserver\_Batchprozesse\status"
python -c "from status import get_last_trading_day; print(f'Erwarteter Handelstag: {get_last_trading_day().strftime(\"%d.%m.%Y\")}')"
```

**1.2 JSON-Status prüfen:**
```powershell
# JSON Timestamp
Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-Object LastWriteTime, Length

# Aktuelles Referenzdatum in JSON
Get-Content "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-String "reference_date" | Select-Object -First 2
```

**1.3 Task und Prozess-Status:**
```powershell
# Task Status
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object State, LastRunTime

# Python Prozesse
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, CPU, StartTime
```

**Problem bestätigt wenn:**
- JSON LastWriteTime ist älter als 2-3 Stunden
- reference_date ist nicht der erwartete letzte Handelstag
- Task zeigt "Running" aber keine JSON-Updates

---

### Schritt 2: Prozess-Aktivität prüfen

**2.1 CPU-Nutzung analysieren:**
```powershell
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, CPU, WorkingSet, StartTime | Format-Table -AutoSize
```

**Interpretation:**
- **CPU < 1 Sekunde nach 2+ Stunden:** Script hängt wahrscheinlich
- **CPU wächst kontinuierlich:** Script läuft, aber möglicherweise in Endlosschleife
- **Prozess startet vor 20+ Stunden:** Sehr wahrscheinlich das Problem

---

### Schritt 3: Code-Version prüfen

**3.1 Prüfen ob der Code aktuell ist:**
```powershell
# status.py Timestamp
Get-Item "D:\Dataserver\_Batchprozesse\status\status.py" | Select-Object LastWriteTime

# Compiled Cache
Get-ChildItem "D:\Dataserver\_Batchprozesse\status\__pycache__\status.cpython-*.pyc" | Select-Object Name, LastWriteTime
```

**3.2 Fix im Code prüfen:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"
grep -A 5 "Prüfe, ob Shares-Daten für den neuen Handelstag verfügbar sind" status.py
```

**Erwartung:** Code sollte den Fix enthalten (nur update wenn Shares verfügbar)

---

### Schritt 4: Grundfunktionen testen

**4.1 Handelstag-Funktionen:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"

# Letzter Handelstag
python -c "from status import get_last_trading_day; result = get_last_trading_day(); print(f'Letzter Handelstag: {result.strftime(\"%d.%m.%Y\")}')"

# Monatlicher Referenztag
python -c "from status import get_last_trading_day_of_previous_month; result = get_last_trading_day_of_previous_month(); print(f'Letzter Handelstag Vormonat: {result.strftime(\"%d.%m.%Y\") if result else \"None\"}')"
```

**4.2 Initialisierung testen:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"
timeout 10 python -c "
from status import initializing
settings = initializing('status.ini', screen=False)
if settings:
    print('Initialisierung: OK')
    print(f'Logfile: {settings.get(\"Files\", {}).get(\"logfile\")}')
    print(f'Refresh Time: {settings.get(\"Timing\", {}).get(\"refresh_time\")}')
else:
    print('Initialisierung: FEHLER')
" 2>&1 | grep -v "INFO:"
```

**4.3 Shares-Verfügbarkeit prüfen:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"
python -c "
import pandas as pd
from datetime import datetime, timedelta
from status import initializing, instruments_import_and_process, bookings_import_and_process, shares_from_bookings, aggregate_banks, get_last_trading_day

settings = initializing('status.ini', screen=False)
logfile = settings.get('Files', {}).get('logfile')
instruments_df = instruments_import_and_process(settings, logfile, screen=False)
bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=False)
end_date = pd.Timestamp(datetime.today().date()) + timedelta(days=30)
shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=False)
shares_day_df = aggregate_banks(shares_day_banks_df)

last_trading_day = get_last_trading_day()
print(f'Letzter Handelstag: {last_trading_day.strftime(\"%d.%m.%Y\")}')
print(f'Shares verfügbar: {last_trading_day in shares_day_df.index.get_level_values(\"date\")}')
print(f'Shares-DataFrame: {shares_day_df.index.get_level_values(\"date\").min().strftime(\"%d.%m.%Y\")} bis {shares_day_df.index.get_level_values(\"date\").max().strftime(\"%d.%m.%Y\")}')
" 2>&1 | grep -v "INFO:"
```

**Wenn alle Tests OK:** Problem liegt nicht an Grundfunktionen, sondern an hängendem Prozess.

---

## Lösung: Service Neustart

### Standard-Neustart (empfohlen)

```powershell
# 1. Task stoppen
Stop-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
Start-Sleep -Seconds 3

# 2. Alle Python-Prozesse beenden
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 3. Cache löschen (optional, aber empfohlen)
Remove-Item "D:\Dataserver\_Batchprozesse\status\__pycache__\status.cpython-*.pyc" -Force -ErrorAction SilentlyContinue

# 4. Task neu starten
Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"

Write-Host "Service neu gestartet. Warte 60 Sekunden auf ersten Update..."
Start-Sleep -Seconds 60
```

### Verifikation nach Neustart

```powershell
# JSON-Update prüfen
Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-Object LastWriteTime

# Referenzdatum prüfen
Get-Content "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-String "reference_date" | Select-Object -First 2

# Task Status
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object State

# Python Prozesse
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, StartTime
```

**Erwartung:**
- JSON LastWriteTime ist innerhalb der letzten 2 Minuten
- reference_date zeigt den korrekten letzten Handelstag
- Task State ist "Running"
- Neue Python-Prozesse mit aktuellem StartTime

---

## Debug-Logs nutzen

**Seit 2025-10-23 enthält status.py Debug-Prints in der Monitoring-Schleife:**

Die Debug-Ausgaben zeigen:
- `=== Monitoring-Durchlauf gestartet ===` - Start jedes Durchlaufs
- `Aktueller Referenztag: XX.XX.XXXX` - Aktuell verwendeter Referenztag
- `Neuer Handelstag: XX.XX.XXXX` - Von get_last_trading_day() ermittelter Tag
- `Sind unterschiedlich? True/False` - Ob Update-Bedingung erfüllt ist
- `Neuer Handelstag erkannt: XX.XX.XXXX` - Wenn Update ausgeführt wird
- `Kurse abgerufen: XX Instrumente` - Nach erfolgreicher API-Abfrage
- `Schreibe JSON mit Referenzdatum: XX.XX.XXXX` - Vor JSON-Schreiben
- `JSON erfolgreich geschrieben` - Nach erfolgreichem JSON-Schreiben

**Problem:** Diese Logs werden nur geschrieben wenn `screen=True` in main() gesetzt ist.

**Temporär Debug-Logs aktivieren:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"

# In status.py Zeile 516 ändern:
# Von:  settings = initializing("status.ini", screen=False)
# Zu:   settings = initializing("status.ini", screen=True)

# Dann Service neu starten (siehe oben)
```

**WICHTIG:** Nach Debugging `screen=False` wieder setzen!

---

## Häufige Ursachen

### 1. Script hängt in while-Schleife (häufigste Ursache)

**Symptome:**
- Prozess läuft seit Stunden/Tagen
- Sehr geringe CPU-Nutzung
- Keine JSON-Updates

**Ursache:**
- Unbekannter stiller Fehler
- Deadlock in der Schleife
- API-Timeout ohne Exception-Handling

**Lösung:** Service-Neustart

---

### 2. Referenzdatum-Update-Logik schlägt fehl

**Symptome:**
- JSON wird aktualisiert
- Aber reference_date bleibt alt

**Mögliche Ursachen:**
- Shares-Daten für neuen Handelstag nicht verfügbar
- get_last_trading_day() gibt falschen Wert zurück
- Vergleich `new_last_trading_day != current_last_trading_day` schlägt fehl

**Diagnose:**
```bash
# Prüfe get_last_trading_day()
python -c "from status import get_last_trading_day; print(get_last_trading_day().strftime('%d.%m.%Y'))"

# Prüfe Shares-Verfügbarkeit (siehe Schritt 4.3)
```

**Lösung:**
- Falls Shares fehlen: Prüfe bookings.xlsx Datei
- Falls get_last_trading_day() falsch: Prüfe holidays-Bibliothek
- Ansonsten: Service-Neustart

---

### 3. API-Probleme (yfinance)

**Symptome:**
- Script startet, aber hängt dann
- Lange Wartezeiten zwischen Updates
- Keine oder unvollständige Kursdaten

**Diagnose:**
```bash
cd "D:\Dataserver\_Batchprozesse\status"
timeout 30 python -c "
from status import initializing, instruments_import_and_process, get_current_prices
import time

settings = initializing('status.ini', screen=False)
logfile = settings.get('Files', {}).get('logfile')
instruments_df = instruments_import_and_process(settings, logfile, screen=False)

print('Teste API-Zugriff...')
start = time.time()
current_prices = get_current_prices(instruments_df)
elapsed = time.time() - start

print(f'Kurse abgerufen: {len(current_prices)} in {elapsed:.1f}s')
if elapsed > 10:
    print('WARNUNG: API ist langsam!')
" 2>&1 | grep -v "INFO:"
```

**Lösung:**
- Warten (API-Probleme sind meist temporär)
- Wenn persistent: Internet-Verbindung prüfen
- refresh_time in status.ini erhöhen

---

## Präventive Maßnahmen

### 1. Monitoring einrichten

**Erstelle Überwachungs-Script:**
```powershell
# check_status_health.ps1
$jsonFile = "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json"
$lastWrite = (Get-Item $jsonFile).LastWriteTime
$age = (Get-Date) - $lastWrite

if ($age.TotalMinutes -gt 120) {
    Write-Host "WARNUNG: JSON wurde seit $($age.TotalMinutes) Minuten nicht aktualisiert!"
    # Optional: Service automatisch neu starten
    # Restart-Service...
} else {
    Write-Host "OK: JSON ist aktuell (vor $([math]::Round($age.TotalMinutes, 1)) Minuten)"
}
```

### 2. Task Scheduler: Täglicher Neustart

**Option:** Erstelle zusätzlichen Task, der den Service täglich neu startet (z.B. um 03:00 Uhr):
- Verhindert lange laufende Prozesse
- Stellt sicher, dass Code-Updates geladen werden
- Räumt Memory auf

---

## Bekannte Probleme

### Problem 1: Referenzdatum bleibt auf altem Wert (Fixed: 2025-10-22)

**Beschreibung:** Siehe CLAUDE.md "Known Issues and Fixes"

**Status:** ✅ Behoben durch Fix in status.py Zeilen 408-420

---

### Problem 2: Script hängt nach Stunden/Tagen (2025-10-23)

**Beschreibung:** Script läuft, aber while-Schleife führt nicht mehr aus.

**Ursache:** Unbekannt (vermutlich silent exception oder Deadlock)

**Workaround:** Regelmäßiger Neustart (manuell oder automatisiert)

**Status:** ⚠️ Beobachten - Debug-Logs wurden hinzugefügt zur besseren Diagnose

---

### Problem 3: PowerShell Starter-Scripts blockieren und Task Scheduler startet nicht neu (Fixed: 2025-10-24)

**Beschreibung:**
- Task Scheduler zeigt Status "Running" aber keine Updates erfolgen
- Nach Server-Neustart startet Task Scheduler den Service nicht neu
- Manuelle Starts über Task Scheduler schlagen fehl mit Error Code 267009 oder 2147946720

**Root Cause:**
Die PowerShell Starter-Scripts (start_status.ps1, start_app.ps1, start_status_dsl.ps1) verwendeten:
```powershell
$pythonResult = & $venvPath -u $pythonScript 2>&1
```

Dieser Aufruf **blockiert** und wartet darauf dass das Python-Script beendet wird. Da status.py, app.py und status_dsl.py aber als **Endlos-Schleifen** laufen (Monitoring-Loop, Flask Webserver), wird das PowerShell-Script nie beendet.

**Probleme:**
1. Task Scheduler denkt der Task läuft (PowerShell-Script läuft ja noch)
2. Task Scheduler startet keinen zweiten Task (nur eine Instanz erlaubt)
3. Nach Server-Neustart: Alter Task ist weg, aber neuer Start findet "Running" Status vor
4. Manuelle Starts schlagen fehl weil Task Scheduler denkt es läuft bereits

**Fix Implemented (2025-10-24):**

Alle drei PowerShell Starter-Scripts wurden angepasst mit **Process Detection vor Start**:

```powershell
# Check if Python script is already running
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$scriptDir*" -or $_.CommandLine -like "*status.py*"
}

if ($pythonProcesses) {
    # Python läuft bereits - Script beendet sofort
    Add-Content -Path $LOGFILE -Value "$timestamp Python script is already running (PIDs: ...)"
    Add-Content -Path $LOGFILE -Value "$timestamp Stock Monitoring Service already active - exiting"
    $RC = 0
} else {
    # Kein Python-Prozess gefunden - starte normal (blockierend)
    $pythonResult = & $venvPath -u $pythonScript 2>&1
    # ... Rest der Logik
}
```

**Vorteile der Lösung:**
1. ✅ Script blockiert weiterhin (PowerShell läuft solange Python läuft)
2. ✅ Task Scheduler kann erkennen dass der Service läuft (Task State = Running)
3. ✅ Zweiter Start erkennt laufenden Prozess und beendet sofort (Exit Code 0)
4. ✅ Nach Server-Neustart: Kein Python-Prozess → Script startet normal
5. ✅ Manuelle Starts funktionieren (wenn noch kein Prozess läuft)
6. ✅ Verhindert doppelte Python-Instanzen

**Betroffene Dateien:**
- `start_status.ps1` - Stock Monitoring Service
- `start_app.ps1` - Flask Web Application
- `start_status_dsl.ps1` - DSL Speedtest Monitoring

**Testing:**
- ✅ Erster Start: Python wird gestartet und läuft korrekt
- ✅ Zweiter Start: Script erkennt laufenden Prozess und beendet sofort
- ✅ JSON wird regelmäßig aktualisiert (Monitoring-Loop läuft)
- ✅ Keine doppelten Python-Prozesse

**Status:** ✅ **GELÖST** (2025-10-24)

---

## Finaler Systemtest: Alle Services prüfen

Nach einem Neustart oder zur routinemäßigen Überprüfung sollten Sie verifizieren dass alle drei Services laufen:

### Schnelltest (empfohlen)

```powershell
# 1. Python-Prozesse zählen (sollte 6 sein: 3 Services mit je 2 Prozessen)
$pythonCount = (Get-Process python -ErrorAction SilentlyContinue).Count
Write-Host "Python Prozesse: $pythonCount (erwartet: 6)"

# 2. Flask Web App (Port 5000 prüfen)
$port5000 = netstat -an | Select-String ':5000.*ABHÖREN'
if ($port5000) {
    Write-Host "✓ Flask Web App läuft (Port 5000)"
} else {
    Write-Host "✗ Flask Web App läuft NICHT"
}

# 3. JSON-Update prüfen (sollte aktuell sein)
$jsonAge = (Get-Date) - (Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json").LastWriteTime
Write-Host "JSON-Alter: $([math]::Round($jsonAge.TotalMinutes, 1)) Minuten (sollte < 2 sein)"

# 4. Logs prüfen (neueste Einträge)
Write-Host "`nLetzter Start:"
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\app_2025-10.log" -Tail 2
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 2
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_dsl_2025-10.log" -Tail 2
```

**Erwartete Ausgabe:**
```
Python Prozesse: 6 (erwartet: 6)
✓ Flask Web App läuft (Port 5000)
JSON-Alter: 0.5 Minuten (sollte < 2 sein)

Letzter Start:
[2025-10-24 08:23:23] Starting Flask application (app.py)...
[2025-10-24 08:05:25] Starting Python script...
[2025-10-24 08:23:24] Starting Python script (status_dsl.py)...
```

### Detaillierter Test (bei Problemen)

```powershell
# Welche Python-Scripts laufen? (verwendet WMI für CommandLine)
Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "python.exe"} |
    Select-Object ProcessId, @{Name='Script';Expression={
        if ($_.CommandLine -like "*status.py*") { "Stock Monitoring" }
        elseif ($_.CommandLine -like "*app.py*") { "Flask Web App" }
        elseif ($_.CommandLine -like "*status_dsl.py*") { "DSL Speedtest" }
        else { "Unbekannt" }
    }} | Format-Table -AutoSize

# Webseite testen (von Server aus)
Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing | Select-Object StatusCode
```

**Erwartete Ausgabe:**
```
ProcessId Script
--------- ------
     4724 Stock Monitoring
     5192 Stock Monitoring
       32 Flask Web App
     6576 Flask Web App
     9824 DSL Speedtest
    10164 DSL Speedtest

StatusCode
----------
       200
```

### Services manuell starten

Falls Services fehlen:

```powershell
cd "D:\Dataserver\_Batchprozesse\status"

# Stock Monitoring starten (falls nicht läuft)
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File start_status.ps1" -WindowStyle Hidden

# Flask Web App starten (falls nicht läuft)
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File start_app.ps1" -WindowStyle Hidden

# DSL Speedtest starten (falls nicht läuft)
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File start_status_dsl.ps1" -WindowStyle Hidden

# 10 Sekunden warten und Status prüfen
Start-Sleep -Seconds 10
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, StartTime | Format-Table -AutoSize
```

---

## Technischer Hinweis: Process Detection

**Problem bei der Entwicklung:**

Die ursprüngliche Implementierung versuchte `Get-Process` mit `.CommandLine` Property zu verwenden:
```powershell
# FUNKTIONIERT NICHT - Get-Process hat kein CommandLine Property
$pythonProcesses = Get-Process -Name "python" | Where-Object {$_.CommandLine -like "*app.py*"}
```

**Lösung:**

Verwendung von `Get-CimInstance Win32_Process` (WMI) um Zugriff auf die CommandLine zu erhalten:
```powershell
# FUNKTIONIERT - WMI/CIM hat CommandLine Property
$pythonProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*app.py*"
}
```

**Warum ist das wichtig?**

- `Get-Process` gibt nur Basis-Prozessinformationen (PID, Name, CPU, Memory, Path)
- `Get-CimInstance Win32_Process` gibt erweiterte Informationen inkl. **CommandLine Arguments**
- Die CommandLine ist nötig um zwischen `status.py`, `app.py` und `status_dsl.py` zu unterscheiden
- Ohne CommandLine würde jeder Python-Prozess als "bereits laufend" erkannt werden

---

## Kontakt und Dokumentation

- **Hauptdokumentation:** CLAUDE.md
- **Deployment-Guide:** DEPLOYMENT.md
- **Changelog:** CHANGELOG_2025-10-22.md
- **Code:** status.py (Zeilen 394-512: run_monitor() Funktion)

---

## Changelog

**2025-10-24:**
- **LÖSUNG IMPLEMENTIERT:** PowerShell Starter-Scripts überarbeitet
- Problem identifiziert: Scripts warteten auf Beendigung von Endlos-Schleifen (status.py, app.py, status_dsl.py)
- Lösung: Process-Detection vor Start - Scripts prüfen ob Python bereits läuft
- Alle drei Starter-Scripts aktualisiert: start_status.ps1, start_app.ps1, start_status_dsl.ps1
- Zweiter Start eines Scripts beendet sofort wenn Prozess bereits läuft
- Verhindert "stuck" Task Scheduler Tasks nach Neustart

**2025-10-23:**
- Initial version erstellt
- Debug-Logs in status.py hinzugefügt
- Standard-Neustart-Prozedur dokumentiert
- Diagnostische Schritte definiert

---

**Ende des Troubleshooting-Guides**
