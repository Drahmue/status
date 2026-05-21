# CHANGELOG - 30. Oktober 2025

## Stock Monitoring Service - Task Scheduler Fehlkonfiguration behoben

**Datum:** 30. Oktober 2025
**Bearbeitet von:** Claude Code + Administrator
**Priorität:** KRITISCH - Service lief nicht seit Server-Neustart am 29.10.2025

---

## PROBLEM-ZUSAMMENFASSUNG

### Symptome
- Stock Monitoring Service wurde in Aufgabenplanung als "wird ausgeführt" angezeigt
- Tatsächlich lief KEIN status.py Prozess
- Keine Log-Updates seit 29.10.2025 00:00:04 (vor Server-Neustart)
- JSON-Daten waren 33+ Stunden veraltet
- Task Scheduler zeigte Exit Code 267009 ("Task läuft noch"), aber kein Prozess vorhanden

### Root Cause
**FEHLERHAFTE TASK-KONFIGURATION:**

Der Task Scheduler versuchte, das PowerShell-Script direkt auszuführen:
```
❌ FALSCH:
Programm/Skript: D:\Dataserver\_Batchprozesse\status\start_status.ps1
Argumente: -ExecutionPolicy Bypass -File
```

**Problem:** Windows kann `.ps1` Dateien nicht direkt als ausführbare Programme starten. Es braucht `powershell.exe` als Programm.

---

## DURCHGEFÜHRTE ANALYSE

### Phase 1: Systemanalyse
- ✅ Logs analysiert (PowerShell, Python, Error-Logs)
- ✅ Prozess-Status geprüft (keine laufenden status.py Prozesse gefunden)
- ✅ Task Scheduler Status geprüft (Zombie-Status "läuft" obwohl nichts läuft)
- ✅ JSON-Dateien geprüft (veraltet seit 33 Stunden)

### Phase 2: Manuelle Tests
- ✅ Script manuell als Administrator gestartet
- ✅ **ERGEBNIS:** Script funktioniert einwandfrei!
  - Initialisierung erfolgreich
  - Netzwerkfreigaben erreichbar
  - Excel-Dateien lesbar
  - yfinance API funktioniert (16/17 Ticker erfolgreich)
  - Endlosschleife läuft stabil

### Phase 3: Task Scheduler Analyse
- ✅ Task-Konfiguration ausgelesen mit `schtasks /query`
- ✅ **FEHLER IDENTIFIZIERT:** Falsche Programm/Argument-Konfiguration

### Phase 4: Vergleich mit funktionierenden Services
- ✅ app.py läuft erfolgreich (korrekte Konfiguration)
- ✅ status_dsl.py läuft erfolgreich (korrekte Konfiguration)
- ❌ status.py läuft NICHT (fehlerhafte Konfiguration)

---

## DURCHGEFÜHRTE ÄNDERUNGEN

### 1. Task Scheduler Zombie-Status behoben
**Zeitpunkt:** 30.10.2025 ~09:55 Uhr

```powershell
# Task gestoppt um Zombie-Status zu beseitigen
Stop-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"

# Ergebnis: State wechselte von "Running" zu "Ready"
```

**Ergebnis:** ✅ Zombie-Status behoben

### 2. Task-Konfiguration repariert
**Zeitpunkt:** 30.10.2025 10:15 Uhr

**Methode:** PowerShell-Script `create_task_complete.ps1` (Version 2)

**Durchgeführte Schritte:**

1. **Alter Task gelöscht:**
   ```powershell
   Unregister-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Confirm:$false
   ```

2. **Automatisierungs-Script erstellt:** `create_task_complete.ps1`
   - Mit expliziter Passwort-Abfrage via `Get-Credential`
   - Grafischer Credential-Dialog öffnet sich automatisch
   - Automatische Task-Registrierung mit korrekter Konfiguration
   - Vollständige Fehlerbehandlung und Diagnose

3. **Script ausgeführt:**
   ```powershell
   .\create_task_complete.ps1
   ```
   - Passwort für User "Service" wurde erfolgreich über grafischen Dialog abgefragt
   - Task wurde erfolgreich registriert mit `-User` und `-Password` Parametern
   - Keine Zeilenumbruch-Probleme dank Script-basiertem Ansatz

**Konfigurationsänderung:**
```diff
- Programm/Skript: D:\Dataserver\_Batchprozesse\status\start_status.ps1
- Argumente: -ExecutionPolicy Bypass -File

+ Programm/Skript: powershell.exe
+ Argumente: -ExecutionPolicy Bypass -File "D:\Dataserver\_Batchprozesse\status\start_status.ps1"
```

**Ergebnis:** ✅ Task erfolgreich konfiguriert und registriert

### 3. Service gestartet und verifiziert
**Zeitpunkt:** 30.10.2025 10:20 Uhr

**Methode:** PowerShell-Script `verify_service.ps1`

**Script erstellt und ausgeführt:**
```powershell
.\verify_service.ps1
```

**Automatische Verifizierungs-Schritte:**
1. ✅ Task gestartet via `Start-ScheduledTask`
2. ✅ 10 Sekunden Wartezeit für Prozess-Start
3. ✅ **Prozess-Prüfung erfolgreich:**
   - Python-Prozess mit status.py läuft
   - **Läuft als User "WIN-H7BKO5H0RMC\Service"** ← Korrekt!
   - Verwendet Virtual Environment `.venv\Scripts\python.exe`
   - CommandLine korrekt: `-u .\status.py`
4. ✅ **Log-Prüfung erfolgreich:**
   - PowerShell Wrapper-Log (`logs\status_2025-10.log`): Neue Einträge mit aktuellem Datum
   - Python Script-Log (`status.log`): "Logger erfolgreich initialisiert", "Starte Monitoring mit Referenzdatum..."
5. ✅ **JSON-Prüfung erfolgreich:**
   - Datei `static\depotdaten.json` wurde aktualisiert
   - Timestamps aktuell
   - Alter < 5 Minuten

**Ergebnis:** ✅ **Service läuft erfolgreich als User "Service" - Problem vollständig behoben!**

### 4. Erstellte Hilfs-Scripts
**Zweck:** Standardisiertes Vorgehen für zukünftige Operationen

- `create_task_complete.ps1` - Task-Erstellung mit Passwort-Abfrage
- `repair_task.ps1` - Teilweise Implementierung (nicht verwendet)
- `verify_service.ps1` - Vollständige Service-Verifizierung

**Hinweis:** Diese temporären Scripts sollen nach erfolgreicher Verifizierung gelöscht werden (siehe "Nächste Schritte")

---

## TECHNISCHE DETAILS

### Warum die alte Konfiguration fehlschlug

**Windows Verhalten:**
1. Task Scheduler versucht, `start_status.ps1` als ausführbare Datei zu starten
2. Windows erkennt `.ps1` als PowerShell-Script
3. Windows versucht, die Standard-Anwendung für `.ps1` zu öffnen
4. Bei Service-User-Kontext schlägt dies fehl (keine UI, keine Datei-Assoziationen)
5. Task wird als "gestartet" markiert, aber Prozess existiert nicht
6. Task Scheduler zeigt "läuft" (Exit Code 267009), aber nichts passiert

**Korrekte Konfiguration:**
1. `powershell.exe` wird als Programm explizit aufgerufen
2. PowerShell erhält das Script als Argument `-File "..."`
3. PowerShell startet erfolgreich auch im Service-Kontext
4. Script läuft wie erwartet

### Vergleich mit anderen Services

**app.py und status_dsl.py verwenden korrekte Konfiguration:**
- Programm: `powershell.exe`
- Argumente: `-ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_app.ps1"`

**status.py verwendete fehlerhafte Konfiguration:**
- Programm: `D:\Dataserver\_Batchprozesse\status\start_status.ps1` ❌
- Argumente: `-ExecutionPolicy Bypass -File`

---

## VERIFIZIERUNG

Nach der Reparatur folgende Checks durchführen:

### 1. Prozess-Check
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*status.py*" } | ForEach-Object {
    $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner
    Write-Host "PID $($_.ProcessId): User=$($owner.Domain)\$($owner.User), StartTime=$($_.CreationDate)"
}
```

**Erwartung:**
- Ein Prozess mit status.py
- User = WIN-H7BKO5H0RMC\Service
- StartTime = kurz nach Task-Start

### 2. Log-Check
```powershell
# PowerShell Wrapper-Log
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 10

# Python Script-Log
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 10
```

**Erwartung:**
- Neue Einträge mit aktuellem Timestamp
- "Starting Stock Monitoring Service"
- "Logger erfolgreich initialisiert"
- "Starte Monitoring mit Referenzdatum: ..."

### 3. JSON-Update-Check
```powershell
Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-Object LastWriteTime
Get-Content "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | ConvertFrom-Json | Select-Object price_timestamp, reference_date
```

**Erwartung:**
- LastWriteTime innerhalb der letzten 2 Minuten
- price_timestamp aktuell
- reference_date = aktueller Handelstag (29.10.2025)

### 4. Task Scheduler Status
```powershell
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Get-ScheduledTaskInfo | Select-Object LastRunTime, LastTaskResult, NextRunTime
```

**Erwartung:**
- LastRunTime = Zeitpunkt des manuellen Starts (oder System-Start)
- LastTaskResult = 267009 (läuft noch) - ist OK, da Endlosschleife
- NextRunTime = N/A (da "AtStartup" Trigger)

---

## LESSONS LEARNED

### 1. Task Scheduler Best Practices
- ✅ **IMMER** `powershell.exe` als Programm verwenden für `.ps1` Scripts
- ✅ **NIEMALS** `.ps1` Datei direkt als Programm angeben
- ✅ Vollständige Pfade in Anführungszeichen verwenden
- ✅ `-ExecutionPolicy Bypass` verwenden für Service-Kontext

### 2. PowerShell Multi-Line Command Best Practices
- ⚠️ **WICHTIG:** Bei langen PowerShell-Befehlen auf Zeilenumbrüche achten!
- ⚠️ Problem: Wenn Befehle mit `>>` (Multi-Line Input) eingegeben werden, können Parameter durch Zeilenumbrüche getrennt werden
- ⚠️ Beispiel: `-Description` und `"Stock price monitoring..."` werden getrennt → Fehler "Missing Argument"
- ⚠️ Problem beim Kopieren: Zeilenumbrüche aus Dokumentation/Chat werden beim Einfügen übernommen
- ✅ **LÖSUNG:** Lange Befehle in logische Blöcke aufteilen und einzeln ausführen
- ✅ **ALTERNATIVE:** Backtick `` ` `` am Zeilenende verwenden für bewusste Fortsetzung
- ✅ **BEST PRACTICE:** Komplexe Task-Erstellung in ein `.ps1` Script auslagern
- ✅ **STANDARDVORGEHEN:** Für komplexe Operationen IMMER PowerShell-Scripts verwenden statt Befehle im Terminal
  - Vorteil: Keine Zeilenumbruch-Probleme
  - Vorteil: Wiederverwendbar und dokumentiert
  - Vorteil: Versionierbar in Git
  - **WICHTIG:** Temporäre Repair-Scripts nach erfolgreicher Ausführung löschen (Aufräumen!)
  - Beispiele: `create_task_complete.ps1`, `repair_task.ps1` etc.

### 3. Debugging-Strategie
- ✅ Erst manuell testen (als Admin) um Code-Probleme auszuschließen
- ✅ Dann Task-Konfiguration prüfen
- ✅ Logs als primäre Diagnosemöglichkeit
- ✅ Prozess-Status mit Owner-Information prüfen

### 3. Wie kam es zu dieser Fehlkonfiguration?
**Hypothese:** Bei der PowerShell-Migration am 22.10.2025 (siehe CHANGELOG_2025-10-22.md) wurde:
- Die Task-Konfiguration für app.py und status_dsl.py korrekt aktualisiert
- Die Task-Konfiguration für status.py **NICHT** oder **FALSCH** aktualisiert
- Möglicherweise durch manuelles Editieren im Task Scheduler GUI statt via PowerShell

**Empfehlung:** Alle Task-Konfigurationen via PowerShell-Script versionieren und dokumentieren.

---

## EMPFEHLUNGEN FÜR DIE ZUKUNFT

### 1. Task-Konfiguration versionieren
Erstellen Sie ein Script zur automatischen Task-Erstellung:

**Datei:** `_Archiv\create_stock_monitoring_task.ps1`
```powershell
# Stock Monitoring Service Task Creator
# Version: 2.0 - Nach Fehlerbehebung vom 30.10.2025

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-ExecutionPolicy Bypass -File "D:\Dataserver\_Batchprozesse\status\start_status.ps1"'
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "Service" -LogonType Password -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Lösche alten Task falls vorhanden
Unregister-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Confirm:$false -ErrorAction SilentlyContinue

# Erstelle neuen Task
Register-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Stock price monitoring and portfolio tracking"

Write-Host "Task erfolgreich erstellt/aktualisiert"
```

### 2. Automatisierter Health-Check
Siehe Empfehlungen im Analysebericht (separates Dokument).

### 3. Einheitliche Task-Verwaltung
Alle drei Services sollten einheitlich verwaltet werden:
- Gleiche Konfigurationsmethode (PowerShell-Scripts)
- Gleiche Logging-Strategie
- Gleiche Monitoring-Mechanismen

---

## DATEIEN GEÄNDERT

### Neu erstellt:
- `CHANGELOG_2025-10-30.md` (diese Datei)

### Task Scheduler:
- `\AHSkripts\Stock Monitoring Service` - Neu konfiguriert

### Nicht geändert:
- `start_status.ps1` - Unverändert (war korrekt)
- `status.py` - Unverändert (war korrekt)
- Alle anderen Dateien

---

## ZEITLINIE DER EREIGNISSE

| Zeitpunkt | Ereignis |
|-----------|----------|
| 29.10.2025 ~12:55 | Server-Neustart |
| 29.10.2025 13:07:25 | Task Scheduler startet "Stock Monitoring Service" (fehlerhaft) |
| 29.10.2025 13:07:25 | Service scheitert sofort, Task zeigt fälschlich "läuft" |
| 30.10.2025 08:50 | **Analyse beginnt** (Claude Code) |
| 30.10.2025 09:05 | Manueller Test als Admin - **Script funktioniert!** |
| 30.10.2025 09:09 | Zweiter manueller Test (CMD) - Bestätigung |
| 30.10.2025 09:55 | Task gestoppt - Zombie-Status behoben |
| 30.10.2025 10:05 | **ROOT CAUSE identifiziert:** Fehlerhafte Task-Konfiguration (`.ps1` direkt statt `powershell.exe`) |
| 30.10.2025 10:10 | Zeilenumbruch-Problem bei Befehls-Eingabe erkannt |
| 30.10.2025 10:15 | **PowerShell-Script erstellt:** `create_task_complete.ps1` (mit Passwort-Abfrage) |
| 30.10.2025 10:15 | Task-Konfiguration erfolgreich repariert via Script |
| 30.10.2025 10:18 | **PowerShell-Script erstellt:** `verify_service.ps1` |
| 30.10.2025 10:20 | Service gestartet und verifiziert - **✅ ERFOLGREICH!** |
| 30.10.2025 10:25 | Changelog aktualisiert, Problem vollständig behoben |

---

## VERANTWORTLICHKEITEN

**Analyse:** Claude Code
**Durchführung:** Administrator
**Verifizierung:** Ausstehend (siehe Verifizierungs-Checks oben)
**Dokumentation:** Dieser Changelog

**Wichtige Hinweise:**
- ✅ Passwort für User "Service" ist bekannt und verfügbar
- ✅ Task-Erstellung erfordert Passwort-Eingabe bei `-LogonType Password`
- ⚠️ Passwort NICHT im Script oder Changelog dokumentieren (Sicherheit!)

---

## NÄCHSTE SCHRITTE

### ✅ Abgeschlossen (30.10.2025):
- [x] Task-Konfiguration reparieren mit `.\create_task_complete.ps1` ✅
- [x] Service starten und verifizieren ✅
- [x] Logs prüfen (erste Updates innerhalb 2 Minuten) ✅
- [x] JSON-Updates prüfen (alle 60 Sekunden) ✅

### Sofort (Aufräumen):
- [ ] **Temporäre Repair-Scripts löschen:**
  - [ ] `create_task_complete.ps1`
  - [ ] `repair_task.ps1`
  - [ ] `verify_service.ps1`
  ```powershell
  Remove-Item create_task_complete.ps1, repair_task.ps1, verify_service.ps1
  ```

### Kurzfristig (diese Woche):
- [ ] **31.10.2025:** Nach 24 Stunden Langzeit-Stabilität verifizieren
  - [ ] Prozess läuft noch?
  - [ ] Logs werden kontinuierlich geschrieben?
  - [ ] JSON wird alle 60 Sekunden aktualisiert?
- [ ] Andere Task-Konfigurationen auditieren (app.py, status_dsl.py)
  - Prüfen ob diese die korrekte Konfiguration haben
- [ ] Permanentes Task-Erstellungs-Script erstellen und in `_Archiv/` speichern
  - Basis: `create_task_complete.ps1` (funktioniert perfekt)

### Mittelfristig (nächste 2 Wochen):
- [ ] Health-Check-Mechanismus implementieren (siehe Stock_Monitoring_Service_Analyse.md)
- [ ] Automatisiertes Monitoring für alle Services einrichten
- [ ] Watchdog-Prozess implementieren (optional)

---

## ANHANG: AUSFÜHRUNGSANWEISUNGEN

### EMPFOHLENES VORGEHEN: PowerShell-Script verwenden

**✅ BESTE METHODE - Keine Zeilenumbruch-Probleme:**

```powershell
# In PowerShell als Administrator ausführen
cd D:\Dataserver\_Batchprozesse\status
.\create_task_complete.ps1
```

Das Script führt alle Schritte automatisch aus und fragt nach dem Passwort für User "Service".

**Nach erfolgreicher Ausführung:**
```powershell
# Temporäre Scripts löschen
Remove-Item create_task_complete.ps1
Remove-Item repair_task.ps1
```

---

### ALTERNATIVE: Manuelle Befehls-Ausführung

**⚠️ NUR FALLS SCRIPT-METHODE NICHT FUNKTIONIERT!**

**⚠️ WICHTIG:** Befehle einzeln ausführen, um Zeilenumbruch-Probleme zu vermeiden!

#### SCHRITT 1: Alten Task löschen
```powershell
Unregister-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Confirm:$false
```

#### SCHRITT 2: Action definieren
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-ExecutionPolicy Bypass -File "D:\Dataserver\_Batchprozesse\status\start_status.ps1"'
```

#### SCHRITT 3: Trigger definieren
```powershell
$trigger = New-ScheduledTaskTrigger -AtStartup
```

#### SCHRITT 4: Principal definieren
```powershell
$principal = New-ScheduledTaskPrincipal -UserId "Service" -LogonType Password -RunLevel Highest
```

#### SCHRITT 5: Settings definieren
```powershell
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
```

#### SCHRITT 6: Task registrieren (HIER kommt Passwort-Abfrage!)
```powershell
Register-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Stock price monitoring and portfolio tracking"
```
**⚠️ Bei diesem Befehl werden Sie nach dem Passwort für User "Service" gefragt!**

#### SCHRITT 7: Task starten
```powershell
Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
```

#### SCHRITT 8: Warten und Prozess verifizieren
```powershell
Start-Sleep -Seconds 10
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*status.py*" } | ForEach-Object {
    $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner
    Write-Host "✅ PID $($_.ProcessId): User=$($owner.Domain)\$($owner.User)"
}
```

#### SCHRITT 9: Logs prüfen
```powershell
Write-Host "`n=== PowerShell Log ===" ; Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 5
Write-Host "`n=== Python Log ===" ; Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 5
```

---

**Ende des Changelogs**
