# CHANGELOG - Stock Monitoring System

**Projekt:** Stock Portfolio Monitoring & DSL Speedtest System
**Letzte Aktualisierung:** 15. Juli 2026
**Version:** 2.2 (PowerShell-basiert)

---

## INHALTSVERZEICHNIS

1. [Status Quo](#status-quo)
2. [Vorgehen für Analyse & Reparatur](#vorgehen-für-analyse--reparatur)
3. [Changelog-Übersicht](#changelog-übersicht)
4. [Alle Änderungen nach Kategorie](#alle-änderungen-nach-kategorie)

---

## STATUS QUO

**Stand:** 30. Oktober 2025, 10:30 Uhr

### Systemübersicht

Das System besteht aus drei Hauptkomponenten, die als Windows Task Scheduler Tasks laufen:

| Service | Status | User | Script | Zweck |
|---------|--------|------|--------|-------|
| **Stock Monitoring Service** | ✅ LÄUFT | Service | `status.py` | Portfolio-Überwachung, Kursabfrage via yfinance |
| **Flask Web App** | ✅ LÄUFT | Service | `app.py` | Web-Interface für Portfolio & Speedtest |
| **DSL Speedtest Monitoring** | ✅ LÄUFT | Service | `status_dsl.py` | Internet-Geschwindigkeits-Monitoring |

### Aktueller Betriebszustand

#### Stock Monitoring Service
- **Prozess-Status:** Läuft als User "Service"
- **Letzter Start:** 30.10.2025 10:20 Uhr
- **Letzte Log-Einträge:** Aktuell (< 5 Minuten)
- **JSON-Updates:** Alle 60 Sekunden
- **Referenzdatum:** 29.10.2025 (aktueller Handelstag)
- **Ticker-Erfolgsrate:** 16/17 (94%)

#### Logs Status
- **PowerShell Wrapper-Log:** `logs\status_2025-10.log` - Aktiv, monatliche Rotation
- **Python Script-Log:** `status.log` - Aktiv
- **Error-Logs:** `logs\status_errors_2025-10.log` - Leer (keine Fehler)
- **Log-Retention:** 120 Tage automatische Bereinigung

#### Daten-Status
- **JSON-Datei:** `static\depotdaten.json` - Aktualisiert alle 60 Sekunden
- **Prices Parquet:** `prices.parquet` - Historische Preisdaten
- **Shares Data:** In-Memory, berechnet aus Excel-Buchungen

#### Task Scheduler Konfiguration
- **Task-Name:** `\AHSkripts\Stock Monitoring Service`
- **Trigger:** Beim Systemstart
- **Programm:** `powershell.exe`
- **Argumente:** `-ExecutionPolicy Bypass -File "D:\Dataserver\_Batchprozesse\status\start_status.ps1"`
- **User:** Service (mit Passwort-Authentifizierung)
- **Run Level:** Highest

### Bekannte Limitierungen
- yfinance API: 1 Ticker (EUN4.DE) liefert keine Daten (delisted)
- Netzwerkfreigaben: 5-Minuten Timeout beim Start (falls Netzwerk nicht verfügbar)
- Excel-Dateien: Liegen auf Netzwerkfreigabe `\\WIN-H7BKO5H0RMC\Dataserver\`

### Letzte erfolgreiche Änderung
- **Datum:** 30.10.2025
- **Problem:** Task Scheduler Fehlkonfiguration (`.ps1` direkt statt `powershell.exe`)
- **Status:** ✅ Behoben
- **Details:** Siehe [CHANGELOG_2025-10-30.md](#changelog_2025-10-30md)

---

## VORGEHEN FÜR ANALYSE & REPARATUR

### Standard-Vorgehensweise

**⚠️ WICHTIG: Für alle komplexen Operationen PowerShell-SCRIPTS verwenden statt manuelle Befehlseingabe!**

Grund: Zeilenumbrüche beim Kopieren aus Dokumentation führen zu Fehlern.

---

### 1. PROBLEM-ANALYSE

#### 1.1 Symptome prüfen

**Service läuft nicht? Folgende Checks durchführen:**

```powershell
# 1. Prozess-Check
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*status.py*" } | ForEach-Object {
    $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner
    Write-Host "PID $($_.ProcessId): User=$($owner.Domain)\$($owner.User)"
}

# 2. Task Scheduler Status
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object TaskName, State

# 3. Task Details
Get-ScheduledTaskInfo -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object LastRunTime, LastTaskResult
```

**Exit Code 267009 bedeutet:** "Task läuft noch" - kann aber falsch sein (Zombie-Status)!

#### 1.2 Logs analysieren

**Log-Dateien Pfade:**

| Log-Typ | Pfad | Zweck |
|---------|------|-------|
| PowerShell Wrapper | `D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log` | Task Scheduler Starter-Script |
| Python Script | `D:\Dataserver\_Batchprozesse\status\status.log` | Python Hauptskript |
| PowerShell Errors | `D:\Dataserver\_Batchprozesse\status\logs\status_errors_2025-10.log` | Wrapper Fehler |
| Python Errors | `D:\Dataserver\_Batchprozesse\status\logs\status_python_errors_2025-10.log` | Python Exceptions |

**Logs prüfen:**

```powershell
# Letzte 20 Zeilen aller Logs
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 20
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 20
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_errors_2025-10.log" -ErrorAction SilentlyContinue

# Live-Monitoring
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Wait
```

#### 1.3 Daten-Status prüfen

```powershell
# JSON-Alter prüfen
$json = Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json"
$age = (Get-Date) - $json.LastWriteTime
Write-Host "JSON-Alter: $([math]::Round($age.TotalMinutes, 1)) Minuten"

# JSON-Inhalt prüfen
Get-Content "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json" | ConvertFrom-Json | Select-Object price_timestamp, reference_date
```

**Erwartung:** JSON sollte < 2 Minuten alt sein (Update alle 60 Sekunden).

---

### 2. MANUELLE TESTS

#### 2.1 Test als Administrator

**Zweck:** Code-Probleme ausschließen, bevor Task-Konfiguration geprüft wird.

```powershell
# In PowerShell als Administrator
cd D:\Dataserver\_Batchprozesse\status
.\.venv\Scripts\python.exe -u .\status.py
```

**Erwartung:**
- ✅ "Logger erfolgreich initialisiert"
- ✅ "Starte Monitoring mit Referenzdatum: ..."
- ✅ Endlosschleife läuft, JSON wird aktualisiert

**Bei Erfolg:** Problem liegt in Task-Konfiguration oder Berechtigungen, NICHT im Code!

#### 2.2 Test als Service-User (falls nötig)

**NUR wenn Test als Admin funktioniert, aber Task nicht:**

```powershell
runas /user:Service "powershell.exe"
# Passwort eingeben
cd D:\Dataserver\_Batchprozesse\status
.\.venv\Scripts\python.exe -u .\status.py
```

**Prüft:** Berechtigungsprobleme für Service-User.

---

### 3. TASK SCHEDULER REPARATUR

#### 3.1 Zombie-Status beheben

**Symptom:** Task zeigt "Wird ausgeführt", aber kein Prozess läuft.

```powershell
# Task stoppen
Stop-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"

# Status prüfen (sollte "Ready" sein)
Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" | Select-Object TaskName, State
```

#### 3.2 Task neu erstellen (KORREKTE METHODE)

**⚠️ WICHTIG: PowerShell-SCRIPT verwenden, NICHT manuelle Befehle!**

**Grund:** Zeilenumbrüche beim Kopieren führen zu Fehlern.

**Script erstellen:** `create_stock_monitoring_task.ps1`

```powershell
# Stock Monitoring Service - Task-Erstellung Script
# Verwendet grafischen Credential-Dialog für Passwort-Eingabe

Write-Host "=== Stock Monitoring Service - Task-Erstellung ===" -ForegroundColor Cyan

# 1. Action definieren
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-ExecutionPolicy Bypass -File "D:\Dataserver\_Batchprozesse\status\start_status.ps1"'

# 2. Trigger definieren
$trigger = New-ScheduledTaskTrigger -AtStartup

# 3. Settings definieren
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 4. Passwort abfragen (öffnet grafischen Dialog)
Write-Host "Gleich öffnet sich ein Passwort-Dialog..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$credential = Get-Credential -UserName "Service" -Message "Passwort für Task Scheduler User 'Service' eingeben"

if (-not $credential) {
    Write-Host "❌ Keine Credentials eingegeben - Abbruch!" -ForegroundColor Red
    exit 1
}

# 5. Alten Task löschen (falls vorhanden)
Unregister-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Confirm:$false -ErrorAction SilentlyContinue

# 6. Task registrieren
$task = Register-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -Action $action -Trigger $trigger -Settings $settings -Description "Stock price monitoring and portfolio tracking" -User $credential.UserName -Password $credential.GetNetworkCredential().Password -Force

Write-Host "✅ Task erfolgreich erstellt!" -ForegroundColor Green
$task | Select-Object TaskName, State | Format-List
```

**Script ausführen:**

```powershell
.\create_stock_monitoring_task.ps1
```

**Wichtige Erkenntnisse:**
- ✅ Grafischer Dialog für Passwort vermeidet Tippfehler
- ✅ Script vermeidet Zeilenumbruch-Probleme
- ✅ `-Force` Parameter überschreibt existierenden Task
- ✅ `-User` und `-Password` Parameter für Credential-Übergabe erforderlich

#### 3.3 Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| "Benutzername oder Kennwort ist falsch" | Falsches Passwort | Script erneut ausführen, korrektes Passwort eingeben |
| "Missing Argument for Description" | Zeilenumbruch in Befehl | Script verwenden statt manuelle Eingabe |
| Exit Code 267009 | Zombie-Status | Task stoppen und neu starten |
| Keine Passwort-Abfrage | `Get-Credential` fehlt | Script verwenden (Version 2) |

---

### 4. SERVICE VERIFIZIERUNG

#### 4.1 Verifizierungs-Script verwenden

**Script erstellen:** `verify_stock_monitoring_service.ps1`

```powershell
# Stock Monitoring Service - Verifizierungs-Script

Write-Host "=== Stock Monitoring Service - Verifizierung ===" -ForegroundColor Cyan

# 1. Task starten
Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
Write-Host "✅ Task gestartet" -ForegroundColor Green

# 2. Warten
Start-Sleep -Seconds 10

# 3. Prozess prüfen
$processes = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*status.py*" }
if ($processes) {
    foreach ($proc in $processes) {
        $owner = Invoke-CimMethod -InputObject $proc -MethodName GetOwner
        Write-Host "✅ Prozess läuft: PID $($proc.ProcessId), User: $($owner.Domain)\$($owner.User)" -ForegroundColor Green
    }
} else {
    Write-Host "❌ KEIN Prozess gefunden!" -ForegroundColor Red
    exit 1
}

# 4. Logs prüfen
Write-Host "`n=== Logs (letzte 5 Zeilen) ===" -ForegroundColor Cyan
Get-Content "D:\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 5

# 5. JSON prüfen
$json = Get-Item "D:\Dataserver\_Batchprozesse\status\static\depotdaten.json"
$age = (Get-Date) - $json.LastWriteTime
Write-Host "`nJSON-Alter: $([math]::Round($age.TotalMinutes, 1)) Minuten" -ForegroundColor $(if($age.TotalMinutes -lt 5){"Green"}else{"Yellow"})

Write-Host "`n✅ Verifizierung abgeschlossen!" -ForegroundColor Green
```

**Script ausführen:**

```powershell
.\verify_stock_monitoring_service.ps1
```

---

### 5. WICHTIGE PFADE & DATEIEN

#### 5.1 PowerShell Scripts

| Script | Pfad | Zweck |
|--------|------|-------|
| **Starter (Wrapper)** | `D:\Dataserver\_Batchprozesse\status\start_status.ps1` | Task Scheduler Starter-Script |
| Flask App Starter | `start_app.ps1` | Web-App Starter |
| DSL Speedtest Starter | `start_status_dsl.ps1` | Speedtest Starter |

**Wichtig:** Alle Starter-Scripts verwenden:
- `Push-Location` für UNC-Pfad-Unterstützung
- Network-Wait-Logic (5 Min. Timeout)
- UTF-8 Encoding
- Monatliche Log-Rotation
- Automatische Log-Cleanup (120 Tage)

#### 5.2 Python Scripts

| Script | Pfad | Zweck |
|--------|------|-------|
| **Stock Monitoring** | `D:\Dataserver\_Batchprozesse\status\status.py` | Hauptskript Portfolio-Monitoring |
| Flask Web App | `app.py` | Web-Interface |
| DSL Speedtest | `status_dsl.py` | Speedtest-Monitoring |

#### 5.3 Konfigurationsdateien

| Datei | Pfad | Zweck |
|-------|------|-------|
| Stock Monitoring Config | `status.ini` | Pfade, Timing, Output-Einstellungen |
| DSL Speedtest Config | `status_dsl.ini` | Ookla CLI Pfad, Server-Settings |

#### 5.4 Daten-Dateien

| Datei | Pfad | Beschreibung |
|-------|------|--------------|
| **JSON Output** | `static\depotdaten.json` | Real-time Portfolio-Daten (Update: 60s) |
| DSL JSON | `static\speedtest.json` | Speedtest-Daten |
| Price History | `prices.parquet` | Historische Kursdaten |
| Speedtest History | `speedtest_data.parquet` | Speedtest-Historie |

#### 5.5 Externe Abhängigkeiten

| Ressource | Pfad | Beschreibung |
|-----------|------|--------------|
| Standard-Bibliothek | `\\WIN-H7BKO5H0RMC\Dataserver\Programmier Projekte\Python\Standardbibliothek\Standardfunktionen_aktuell.py` | ahlib (Logging, File-Ops) |
| Instrumente Excel | `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx` | Ticker, WKN, Namen |
| Buchungen Excel | `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx` | Transaktionshistorie |

---

### 6. BEST PRACTICES & LESSONS LEARNED

#### 6.1 PowerShell-Scripts statt Befehle

**❌ NICHT:**
```powershell
# Manuelle Eingabe mit Zeilenumbrüchen führt zu Fehlern
Register-ScheduledTask -TaskName "..." -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings -Description
  "Stock price monitoring..."  # ← Fehler: Description getrennt!
```

**✅ STATTDESSEN:**
```powershell
# Script erstellen und ausführen
.\create_task.ps1
```

**Gründe:**
- Keine Zeilenumbruch-Probleme beim Kopieren
- Wiederverwendbar
- Versionierbar in Git
- Dokumentiert das Vorgehen

#### 6.2 Passwort-Eingabe

**❌ NICHT:** Passwort im Script hart-codieren

**✅ STATTDESSEN:** Grafischen Dialog verwenden
```powershell
$credential = Get-Credential -UserName "Service" -Message "Passwort eingeben"
```

**Vorteile:**
- Sicher (kein Klartext im Script)
- Grafischer Dialog vermeidet Tippfehler
- Standard Windows-Mechanismus

#### 6.3 Task Scheduler Konfiguration

**❌ FALSCH:**
```
Programm/Skript: D:\...\start_status.ps1
Argumente: -ExecutionPolicy Bypass -File
```
→ Windows kann `.ps1` nicht direkt als Programm ausführen!

**✅ KORREKT:**
```
Programm/Skript: powershell.exe
Argumente: -ExecutionPolicy Bypass -File "D:\...\start_status.ps1"
```
→ PowerShell wird explizit aufgerufen, funktioniert im Service-Kontext!

#### 6.4 Debugging-Strategie

**Reihenfolge:**
1. ✅ **Erst** manuell als Admin testen → Code-Probleme ausschließen
2. ✅ **Dann** Task-Konfiguration prüfen → Konfigurations-Probleme
3. ✅ **Zuletzt** als Service-User testen → Berechtigungs-Probleme

**Nicht umgekehrt!** Sonst verschwendet man Zeit mit Berechtigungen, obwohl der Code fehlerhaft ist.

#### 6.5 Temporäre Scripts aufräumen

**Nach erfolgreicher Reparatur:**
```powershell
Remove-Item create_task_complete.ps1, verify_service.ps1, repair_task.ps1
```

**Grund:** Temporäre Scripts sollten nicht dauerhaft im Repository bleiben.

**Aber:** Permanente Versions-Scripts in `_Archiv/` speichern für zukünftige Verwendung.

---

### 7. TROUBLESHOOTING QUICK REFERENCE

#### Symptom: Task zeigt "Wird ausgeführt", aber kein Prozess

**Ursache:** Zombie-Status (Prozess ist sofort abgestürzt)

**Lösung:**
```powershell
Stop-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
Start-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
```

#### Symptom: Logs werden nicht aktualisiert

**Ursache 1:** Prozess läuft nicht
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*status.py*" }
```

**Ursache 2:** Log-Verzeichnis nicht beschreibbar
```powershell
Test-Path "D:\Dataserver\_Batchprozesse\status\logs\"
```

#### Symptom: JSON veraltet (> 2 Minuten)

**Ursache:** Monitoring-Schleife läuft nicht oder yfinance API schlägt fehl

**Lösung:** Python-Log prüfen auf Fehler
```powershell
Get-Content "D:\Dataserver\_Batchprozesse\status\status.log" -Tail 50 | Select-String "ERROR|Exception|Traceback"
```

#### Symptom: "Benutzername oder Kennwort ist falsch"

**Ursache:** Falsches Passwort für User "Service"

**Lösung:** Script erneut ausführen, korrektes Passwort eingeben via Credential-Dialog

---

## CHANGELOG-ÜBERSICHT

### Detail-Changelogs (Chronologisch)

| Datum | Datei | Zusammenfassung | Priorität |
|-------|-------|-----------------|-----------|
| **15.07.2026** | [CHANGELOG_2026-07-15.md](./CHANGELOG_2026-07-15.md) | 🔧 Server-Neuaufsetzen (WS2022→WS2025): NTFS-Permission-Bug (Errno 13) + fehlender SSH-Zugriff für Git-Push behoben | 🔴 CRITICAL |
| **22.05.2026** | [CHANGELOG_2026-05-21.md](./CHANGELOG_2026-05-21.md) | 📱 Responsive Design — Statusseite skaliert auf Desktop, Tablet, Smartphone, Z Fold | 🟢 MINOR |
| **21.05.2026** | [CHANGELOG_2026-05-21.md](./CHANGELOG_2026-05-21.md) | 🌐 Tailscale VPN eingerichtet — externer Zugriff via `http://hauserver:5000` | 🟢 MINOR |
| **21.05.2026** | [CHANGELOG_2026-05-21.md](./CHANGELOG_2026-05-21.md) | 📊 Zählerstand-Monitoring (Gas & Strom via Tasmota) hinzugefügt | 🟡 MAJOR |
| **27.02.2026** | [CHANGELOG_2026-02-27.md](./CHANGELOG_2026-02-27.md) | 🔧 ExecutionTimeLimit Bug + Silent Crash in run_monitor() behoben | 🔴 CRITICAL |
| **30.10.2025** | [CHANGELOG_2025-10-30.md](./CHANGELOG_2025-10-30.md) | ⚠️ **CRITICAL:** Task Scheduler Fehlkonfiguration behoben - Service lief nicht seit Server-Neustart | 🔴 CRITICAL |
| **22.10.2025** | [CHANGELOG_2025-10-22.md](./CHANGELOG_2025-10-22.md) | 🔄 PowerShell Migration, Zentralisierte Logs, Automatisierte Tests | 🟡 MAJOR |
| **20.10.2025** | [CHANGELOG_2025-10-20.md](./CHANGELOG_2025-10-20.md) | 🔧 UNC Path Problem gelöst, Initiale PowerShell-Konvertierung | 🟢 MINOR |
| **17.10.2025** | [CHANGELOG_2025-10-17.md](./CHANGELOG_2025-10-17.md) | 🔧 Network Wait Logic implementiert für zuverlässigen Startup | 🟢 MINOR |

### Zusammenfassung nach Detail-Changelog

#### CHANGELOG_2025-10-30.md
**Status:** ✅ Erfolgreich behoben
**Problem:** Stock Monitoring Service zeigte "Wird ausgeführt" in Aufgabenplanung, lief aber nicht.
**Root Cause:** Fehlerhafte Task Scheduler Konfiguration - `.ps1` direkt als Programm statt `powershell.exe`
**Lösung:**
- Task-Konfiguration repariert via PowerShell-Script
- Korrekte Konfiguration: `powershell.exe` mit `-File` Argument
- Service läuft jetzt erfolgreich als User "Service"

**Wichtigste Erkenntnisse:**
- PowerShell-Scripts verwenden statt manuelle Befehle (Zeilenumbruch-Problem)
- Grafischer Credential-Dialog für Passwort-Eingabe
- Erst manuell testen (Code), dann Task-Konfiguration prüfen

#### CHANGELOG_2025-10-22.md
**Änderungen:**
- Migration von Batch zu PowerShell für alle Starter-Scripts
- Zentralisierte Logs in `logs/` Verzeichnis mit monatlicher Rotation
- Automatische Log-Cleanup (120 Tage)
- Automatisierte Tests mit Service-Account-Authentifizierung
- Task Scheduler Tasks aktualisiert auf PowerShell
- Deployment-Dokumentation auf Version 2.0

#### CHANGELOG_2025-10-20.md
**Änderungen:**
- UNC Path Problem gelöst via `Push-Location`
- Erste Batch-zu-PowerShell Konvertierung
- UTF-8 Encoding-Unterstützung

#### CHANGELOG_2025-10-17.md
**Änderungen:**
- Network Wait Logic implementiert (3-5 Minuten Timeout)
- Zuverlässiger Service-Start bei System-Boot
- Prüfung auf Netzwerkfreigabe-Verfügbarkeit vor Script-Start

---

## ALLE ÄNDERUNGEN NACH KATEGORIE

### 🔴 Critical Fixes

| Datum | Problem | Lösung | Status |
|-------|---------|--------|--------|
| 15.07.2026 | Permission denied (Errno 13) nach Server-Neuaufsetzen - Service-Account hatte nur RX statt Modify auf Finance_Input | NTFS-ACL korrigiert via `icacls /grant Service:(OI)(CI)M` | ✅ Behoben |
| 30.10.2025 | Service lief nicht - Task Scheduler Fehlkonfiguration | Task neu erstellt mit korrekter Konfiguration (`powershell.exe` statt `.ps1` direkt) | ✅ Behoben |
| 22.10.2025 | Reference Date Update Bug - Datum wurde nicht aktualisiert | Logic-Fix in `run_monitor()` - nur updaten wenn Shares-Daten verfügbar | ✅ Behoben |

### 🔧 Major Changes

| Datum | Änderung | Auswirkung |
|-------|----------|------------|
| 22.10.2025 | PowerShell Migration | Alle Starter-Scripts von `.bat` zu `.ps1` migriert |
| 22.10.2025 | Zentralisierte Logs | Logs jetzt in `logs/` mit monatlicher Rotation |
| 22.10.2025 | Automatisierte Tests | PowerShell Test-Framework mit Service-Account |

### 🔨 Minor Improvements

| Datum | Verbesserung | Details |
|-------|--------------|---------|
| 21.05.2026 | Tailscale externer Zugriff | Statusseite via `http://hauserver:5000` von ahflipalt, ahfold, ahlap erreichbar — ohne offene Ports |
| 22.10.2025 | Log-Cleanup | Automatische Bereinigung von Logs > 120 Tage |
| 22.10.2025 | Emergency Logging | Fallback zu `C:\Temp\` wenn `logs/` nicht verfügbar |
| 20.10.2025 | UNC Path Support | `Push-Location` für Netzwerkfreigaben |
| 17.10.2025 | Network Wait Logic | 3-5 Minuten Timeout für Netzwerk-Verfügbarkeit |

### 📝 Documentation

| Datum | Dokument | Beschreibung |
|-------|----------|--------------|
| 30.10.2025 | CHANGELOG.md (Master) | Umfassende Übersicht + Runbook für Analyse & Reparatur |
| 30.10.2025 | CHANGELOG_2025-10-30.md | Task Scheduler Fehlkonfiguration Behebung |
| 22.10.2025 | DEPLOYMENT.md v2.0 | PowerShell-basierte Deployment-Anleitung |
| 22.10.2025 | CHANGELOG_2025-10-22.md | PowerShell Migration Dokumentation |

### 🧪 Testing & Quality Assurance

| Datum | Test/Tool | Zweck |
|-------|-----------|-------|
| 30.10.2025 | `create_task_complete.ps1` | Automatisierte Task-Erstellung mit Passwort-Abfrage |
| 30.10.2025 | `verify_service.ps1` | Vollständige Service-Verifizierung |
| 22.10.2025 | `test_as_service_with_password.ps1` | Automatisierte Tests als Service-User |

---

## SYSTEM-ARCHITEKTUR

### Komponenten-Übersicht

```
Windows Task Scheduler
├── Stock Monitoring Service (start_status.ps1 → status.py)
│   ├── Reads: Instrumente.xlsx, bookings.xlsx
│   ├── Fetches: yfinance API (prices)
│   └── Outputs: depotdaten.json, prices.parquet
│
├── Flask Web App (start_app.ps1 → app.py)
│   ├── Reads: depotdaten.json, speedtest.json
│   └── Serves: HTTP on localhost:5000
│
└── DSL Speedtest (start_status_dsl.ps1 → status_dsl.py)
    ├── Executes: Ookla CLI or Python speedtest
    └── Outputs: speedtest.json, speedtest_data.parquet
```

### Datenfluss

```
Excel (Network Share)
  └→ Instrumente.xlsx, bookings.xlsx
      └→ status.py (Portfolio berechnen)
          └→ yfinance API (Kurse abrufen)
              └→ depotdaten.json
                  └→ app.py (Web-Interface)
                      └→ Browser (Nutzer)
```

---

## BEKANNTE PROBLEME & WORKAROUNDS

| Problem | Workaround | Status |
|---------|------------|--------|
| yfinance Ticker EUN4.DE liefert keine Daten | Akzeptiert (delisted), andere 16/17 funktionieren | ⚠️ Bekannt |
| Network Share Verfügbarkeit beim Boot | Network Wait Logic (5 Min Timeout) | ✅ Implementiert |
| Zeilenumbrüche bei PowerShell-Befehlen | Scripts verwenden statt manuelle Eingabe | ✅ Dokumentiert |

---

## ZUKÜNFTIGE VERBESSERUNGEN

### Kurzfristig (diese Woche)
- [ ] 24h-Stabilitäts-Verifizierung (31.10.2025)
- [ ] Audit der anderen Task-Konfigurationen (app.py, status_dsl.py)
- [ ] Permanentes Task-Erstellungs-Script in `_Archiv/` speichern

### Mittelfristig (nächste 2 Wochen)
- [ ] Health-Check-Mechanismus implementieren
- [ ] Automatisiertes Monitoring für alle Services
- [ ] Watchdog-Prozess (optional)

### Langfristig
- [ ] Migration zu Windows Service (statt Task Scheduler)
- [ ] Web-basiertes Admin-Interface
- [ ] Email-Benachrichtigungen bei Ausfällen

---

## KONTAKT & SUPPORT

**Bei Problemen:**
1. Dieses Changelog konsultieren → [Vorgehen für Analyse & Reparatur](#vorgehen-für-analyse--reparatur)
2. Detail-Changelog für spezifisches Problem lesen
3. PowerShell-Scripts verwenden (nicht manuelle Befehle!)
4. Logs analysieren vor Task-Neustart

**Wichtige Erinnerung:**
- ✅ PowerShell-Scripts verwenden (keine Zeilenumbruch-Probleme)
- ✅ Passwort via grafischen Dialog eingeben (Get-Credential)
- ✅ Erst manuell testen (Code), dann Task prüfen (Konfiguration)
- ✅ Temporäre Scripts nach erfolgreicher Reparatur löschen

---

**Ende des Master-Changelogs**

*Letzte Aktualisierung: 30. Oktober 2025, 10:30 Uhr*
