# Changelog - 2025-10-20

## Zusammenfassung

Behebung des kritischen UNC-Pfad Problems in `start_status.bat` durch Konvertierung zu PowerShell (`start_status.ps1`). Das Problem verhinderte, dass der Task nach dem Server-Neustart vom 17.10.2025 ordnungsgemäß starten konnte.

## Problem

Nach der Implementierung der Verbesserungen vom 17.10.2025 konnte der Task "Stock Monitoring Service" weiterhin nicht automatisch starten. Eine detaillierte Analyse ergab:

### Root Cause

Die Batch-Datei `start_status.bat` verwendete einen **UNC-Pfad** als Arbeitsverzeichnis:
```batch
set SCRIPT_DIR=\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
cd /d "%SCRIPT_DIR%"
```

**Windows-Limitation:** Das `cd /d` Kommando in Batch-Dateien kann **nicht** zu UNC-Pfaden wechseln. Dies ist eine fundamentale Windows-Einschränkung.

### Fehlersymptom

```
[20.10.2025 14:00:59] Starting Stock Monitoring Service
[20.10.2025 14:00:59] Running as user: Administrator
[20.10.2025 14:00:59] ERROR: Failed to change to directory \\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
```

Der Task startete, scheiterte aber sofort beim Versuch, zum UNC-Pfad zu wechseln (Zeile 19-23 in `start_status.bat`).

### Warum funktionierte es vorher?

- Die älteren Logs zeigten erfolgreiche Läufe im September
- Nach dem Server-Neustart am 17.10.2025 um 15:37:16 trat das Problem auf
- Die Änderungen vom 17.10.2025 adressierten Netzwerk-Timing, aber nicht das UNC-Pfad Problem

## Durchgeführte Änderungen

### Neue Datei: `start_status.ps1`

Komplette Neuentwicklung als PowerShell-Script, basierend auf dem bewährten Pattern von `depot\start_depot.ps1`.

**Datei erstellt:** `start_status.ps1`

#### Hauptmerkmale

1. **UNC-Pfad Unterstützung**
   - PowerShell's `Push-Location` unterstützt UNC-Pfade nativ
   - Kein Workaround mit gemappten Laufwerken notwendig

2. **Netzwerk-Wartelogik**
   ```powershell
   # 5 Minuten Timeout (60 Versuche × 5 Sekunden)
   $MAX_NETWORK_WAIT = 60
   $WAIT_INTERVAL_SECONDS = 5
   ```
   - Prüft Netzwerkfreigabe-Root
   - Prüft `Instrumente.xlsx`
   - Prüft `bookings.xlsx`
   - Wartet bis zu 5 Minuten auf Verfügbarkeit

3. **Monatliche Log-Dateien**
   ```powershell
   $LOGFILE = "$LOGDIR\status_YYYY-MM.log"
   $ERRORLOG = "$LOGDIR\status_errors_YYYY-MM.log"
   ```
   - Folgt dem depot-Script Pattern
   - Automatische Bereinigung (> 120 Tage werden gelöscht)

4. **Umfassende Fehlerbehandlung**
   - Try-Catch Blöcke für alle kritischen Operationen
   - Separate Error-Log Datei
   - Fallback auf `C:\Temp` wenn Log-Verzeichnis nicht erreichbar

5. **UTF-8 Encoding**
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   $env:PYTHONIOENCODING = "utf-8"
   ```
   - Vollständige Unterstützung für deutsche Umlaute

6. **Robuste Vorbedingungsprüfung**
   - Virtual Environment Existenz
   - Python Script Existenz
   - Alle Netzwerk-Ressourcen verfügbar

#### Funktionsweise

```powershell
function Wait-ForNetworkResources {
    # Wartet bis zu 5 Minuten auf:
    # 1. Netzwerkfreigabe Root
    # 2. Instrumente.xlsx
    # 3. bookings.xlsx
    # Gibt $true zurück wenn alle verfügbar, sonst $false
}
```

Das Script:
1. Initialisiert Logging
2. Wartet auf Netzwerk-Ressourcen (max. 5 Min)
3. Wechselt zum UNC-Pfad mit `Push-Location`
4. Prüft Virtual Environment und Python Script
5. Startet `status.py` (läuft kontinuierlich in Schleife)
6. Loggt alle Ausgaben
7. Bereinigt alte Logs
8. Gibt korrekten Exit Code zurück

## Test-Ergebnisse

Das neue PowerShell-Script wurde erfolgreich getestet:

```
[2025-10-20 14:06:25] Starting Stock Monitoring Service
[2025-10-20 14:06:25] Running as user: Administrator
[2025-10-20 14:06:25] Checking network resource availability...
[2025-10-20 14:06:25] Network share \\WIN-H7BKO5H0RMC\Dataserver is available
[2025-10-20 14:06:25] All required files are accessible
[2025-10-20 14:06:25] Changed directory to: \\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
[2025-10-20 14:06:25] Starting Python script...
```

**Verifikation:**
- ✅ UNC-Pfad erfolgreich gemountet
- ✅ Netzwerk-Ressourcen gefunden
- ✅ Python Script gestartet
- ✅ JSON-Datei wird aktiv aktualisiert (`depotdaten.json`, letztes Update: 14:07:20)
- ✅ Keine Fehler im Log

## Nächste Schritte - Task Scheduler Update ERFORDERLICH

Der Task Scheduler muss manuell aktualisiert werden, um das neue PowerShell-Script zu verwenden:

### Anleitung

1. **Task Scheduler öffnen**
   ```
   Start → Task Scheduler (Aufgabenplanung)
   ```

2. **Task suchen**
   - Suche nach: `Stock Monitoring Service`

3. **Task bearbeiten**
   - Rechtsklick → Eigenschaften
   - Tab "Aktionen" auswählen
   - Bestehende Aktion bearbeiten

4. **Neue Aktion konfigurieren**

   **Programm/Skript:**
   ```
   powershell.exe
   ```

   **Argumente hinzufügen:**
   ```
   -ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_status.ps1"
   ```

   **Starten in:**
   ```
   (leer lassen - PowerShell behandelt UNC-Pfade)
   ```

5. **Trigger prüfen**
   - Bestätigen, dass der Trigger "Beim Start" mit 2-Minuten Verzögerung konfiguriert ist
   - Bei Bedarf anpassen

6. **Speichern und Testen**
   - Task speichern
   - Rechtsklick → "Ausführen" für sofortigen Test
   - Log-Datei prüfen: `D:\Dataserver\_Batchprozesse\status\status_2025-10.log`

### Alternative: PowerShell Kommando zur Task-Aktualisierung

```powershell
# Als Administrator ausführen
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_status.ps1"'

Set-ScheduledTask -TaskName "Stock Monitoring Service" -Action $action
```

## Vergleich: Alt vs. Neu

| Aspekt | start_status.bat | start_status.ps1 |
|--------|------------------|------------------|
| **UNC-Pfad Support** | ❌ Nicht möglich | ✅ Nativ unterstützt |
| **Netzwerk Timeout** | 10 Minuten (120×5s) | 5 Minuten (60×5s) |
| **Logging** | Einzelne Datei | Monatliche Rotation |
| **Error Handling** | Basic | Comprehensive |
| **Encoding** | Problematisch | UTF-8 guaranteed |
| **Alte Logs Cleanup** | ❌ Nein | ✅ Ja (>120 Tage) |
| **Separate Error Log** | ❌ Nein | ✅ Ja |

## Vorteile der neuen Lösung

1. **UNC-Pfad Kompatibilität**
   - Funktioniert direkt mit Netzwerkfreigaben
   - Keine Abhängigkeit von gemappten Laufwerken
   - Service-Account benötigt keine Drive-Mappings

2. **Verbesserte Wartbarkeit**
   - Monatliche Log-Rotation
   - Automatische Bereinigung alter Logs
   - Separate Error-Logs für schnellere Diagnose

3. **Robustere Fehlerbehandlung**
   - Try-Catch Blöcke überall
   - Fallback-Mechanismen
   - Detaillierte Fehlermeldungen

4. **Konsistenz**
   - Folgt etabliertem Pattern von `depot\start_depot.ps1`
   - Einheitliche Struktur über alle Monitoring-Services

5. **Reduzierter Timeout**
   - 5 statt 10 Minuten (ausreichend für normale Server-Startzeiten)
   - Schnelleres Feedback bei echten Problemen

## Rollback (falls notwendig)

Falls das PowerShell-Script Probleme verursacht:

### Option 1: Task Scheduler zurücksetzen

```
Programm/Skript: D:\Dataserver\_Batchprozesse\status\start_status.bat
Argumente: (leer)
Starten in: D:\Dataserver\_Batchprozesse\status
```

**Hinweis:** Die alte Batch-Datei hat weiterhin das UNC-Pfad Problem!

### Option 2: Batch-Datei mit lokalem Pfad

Falls der UNC-Pfad wirklich notwendig ist, muss die Batch-Datei modifiziert werden:

```batch
REM Änderung in start_status.bat:
set SCRIPT_DIR=D:\Dataserver\_Batchprozesse\status
```

**Aber:** Dies funktioniert nur, wenn der physische Server `D:\` hat, nicht remote.

## Verifizierung des laufenden Services

Um zu überprüfen, ob der "Stock Monitoring Service" erfolgreich läuft, können folgende Methoden verwendet werden:

### Methode 1: Task Scheduler Status prüfen (PowerShell)

```powershell
# Task Status anzeigen
Get-ScheduledTask -TaskName "Stock Monitoring Service" | Select-Object TaskName, State, LastRunTime, LastTaskResult | Format-List
```

**Erwartete Ausgabe bei laufendem Service:**
```
TaskName       : Stock Monitoring Service
State          : Running
LastRunTime    :
LastTaskResult :
```

### Methode 2: Log-Datei prüfen

```powershell
# Letzte Einträge der aktuellen monatlichen Log-Datei anzeigen
Get-Content "D:\Dataserver\_Batchprozesse\status\status_2025-10.log" -Tail 20
```

**Erfolgreiche Startmeldungen:**
```
[2025-10-20 14:06:25] Starting Stock Monitoring Service
[2025-10-20 14:06:25] Running as user: Administrator
[2025-10-20 14:06:25] Checking network resource availability...
[2025-10-20 14:06:25] Network share \\WIN-H7BKO5H0RMC\Dataserver is available
[2025-10-20 14:06:25] All required files are accessible
[2025-10-20 14:06:25] Changed directory to: \\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
[2025-10-20 14:06:25] Starting Python script...
```

### Methode 3: Datenaktualisierung prüfen

```powershell
# Zeitstempel der letzten JSON-Aktualisierung prüfen
(Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json").LastWriteTime
```

**Interpretation:**
- Wenn die Datei regelmäßig aktualisiert wird (alle paar Minuten), läuft der Service korrekt
- Alte Zeitstempel deuten auf Probleme hin

### Methode 4: Python-Prozesse zählen

```powershell
# Anzahl der laufenden Python-Prozesse
Get-Process python -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count
```

**Erwartete Ausgabe:**
- Mindestens 1 Python-Prozess sollte laufen (status.py)
- Bei zusätzlichen Services (status_dsl.py) entsprechend mehr

### Vollständige Verifikation (Alle Checks kombiniert)

```powershell
# Komplettes Verifikations-Script
Write-Host "=== Stock Monitoring Service Status ===" -ForegroundColor Cyan

# 1. Task Status
Write-Host "`n1. Task Scheduler Status:" -ForegroundColor Yellow
Get-ScheduledTask -TaskName "Stock Monitoring Service" | Select-Object TaskName, State | Format-List

# 2. Log-Datei
Write-Host "2. Letzte Log-Einträge:" -ForegroundColor Yellow
$currentMonth = Get-Date -Format "yyyy-MM"
$logFile = "D:\Dataserver\_Batchprozesse\status\status_$currentMonth.log"
if (Test-Path $logFile) {
    Get-Content $logFile -Tail 5
} else {
    Write-Host "Log-Datei nicht gefunden: $logFile" -ForegroundColor Red
}

# 3. Datenaktualisierung
Write-Host "`n3. Letzte Datenaktualisierung:" -ForegroundColor Yellow
$jsonFile = "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json"
if (Test-Path $jsonFile) {
    $lastUpdate = (Get-Item $jsonFile).LastWriteTime
    Write-Host "depotdaten.json: $lastUpdate"
    $minutesAgo = ((Get-Date) - $lastUpdate).TotalMinutes
    Write-Host "Vor $([math]::Round($minutesAgo, 1)) Minuten aktualisiert"
} else {
    Write-Host "JSON-Datei nicht gefunden!" -ForegroundColor Red
}

# 4. Python-Prozesse
Write-Host "`n4. Laufende Python-Prozesse:" -ForegroundColor Yellow
$pythonCount = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "$pythonCount Python-Prozesse aktiv"

Write-Host "`n=== Verifikation abgeschlossen ===" -ForegroundColor Cyan
```

## Weitere Empfehlungen

1. **Nach Server-Neustart prüfen**
   - Neustarten des Servers zur Verifikation
   - Log-Datei prüfen: `status_2025-10.log` oder aktueller Monat
   - Verwenden Sie die oben beschriebenen Verifizierungsmethoden
   - Bestätigen, dass Task automatisch startet

2. **Monitoring**
   - Prüfen Sie regelmäßig die Error-Logs: `status_errors_YYYY-MM.log`
   - Alte Log-Dateien werden automatisch nach 120 Tagen gelöscht
   - Nutzen Sie das vollständige Verifikations-Script für regelmäßige Checks

3. **Weitere Tasks**
   - Erwägen Sie, auch andere Tasks auf PowerShell zu migrieren
   - Insbesondere wenn diese UNC-Pfade verwenden

## Geänderte/Neue Dateien

- **NEU:** `start_status.ps1` (PowerShell-Version, vollständiger Ersatz)
- **UNVERÄNDERT:** `start_status.bat` (als Fallback erhalten)
- **NEU:** `CHANGELOG_2025-10-20.md` (dieses Dokument)

## Referenzen

- **Vorheriges CHANGELOG:** `CHANGELOG_2025-10-17.md`
- **Verwandtes Script:** `D:\Dataserver\_Batchprozesse\depot\start_depot.ps1`
- **Log-Dateien:**
  - Neu: `status_YYYY-MM.log` (monatlich)
  - Alt: `task_scheduler.log` (einzelne Datei)
- **Issue:** UNC-Pfad Limitation in Windows Batch-Dateien
- **Task Name:** "Stock Monitoring Service"

## Autor

Claude Code - 2025-10-20

## Technische Details

### Windows UNC-Pfad Limitationen

**Batch (`cmd.exe`):**
```batch
cd /d \\server\share\folder  # FEHLER: CMD unterstützt UNC nicht als CWD
```

**PowerShell:**
```powershell
Push-Location \\server\share\folder  # Funktioniert einwandfrei
```

**Grund:** Windows CMD.exe kann UNC-Pfade nicht als "Current Working Directory" setzen. Dies ist eine bekannte Limitation seit Windows NT. PowerShell verwendet einen anderen Mechanismus (PSDrives), der UNC-Pfade nativ unterstützt.

### Service Account Überlegungen

- **Gemappte Laufwerke:** Funktionieren NICHT für Service Accounts (per-user)
- **UNC-Pfade:** Funktionieren mit korrekten Berechtigungen
- **PowerShell:** Benötigt ExecutionPolicy Bypass für UNC-Pfad Scripts

### Execution Policy

```powershell
-ExecutionPolicy Bypass
```
Erforderlich weil:
1. Script läuft von UNC-Pfad
2. Keine Code-Signatur vorhanden
3. RemoteSigned würde UNC-Scripts blockieren
