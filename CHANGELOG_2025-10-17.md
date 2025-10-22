# Changelog - 2025-10-17

## Zusammenfassung

Behebung des Exit Code 2 Problems bei `start_status.bat`, das nach einem Server-Neustart auftrat, wenn die Netzwerkfreigaben noch nicht vollständig verfügbar waren.

## Problem

Nach dem Server-Neustart schlug `start_status.bat` mit Exit Code 2 fehl, weil das Python-Skript `status.py` die benötigten Excel-Dateien auf der Netzwerkfreigabe nicht finden konnte:

```
[2025-10-17 16:08:04] ERROR: Datei '\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx' nicht gefunden.
[2025-10-17 16:08:04] ERROR: Datei '\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx' nicht gefunden.
```

**Ursache:** Die Batch-Datei prüfte nur die Verfügbarkeit des Root-Verzeichnisses der Netzwerkfreigabe, nicht aber die tatsächlich benötigten Dateien in den Unterverzeichnissen.

## Durchgeführte Änderungen

### Datei: `start_status.bat`

**Backup erstellt:** `start_status.bat.backup_2025-10-17`

#### Änderung 1: Erhöhung der maximalen Wartezeit
- **Vorher:** `MAX_NETWORK_WAIT=60` (5 Minuten bei 5 Sekunden pro Versuch)
- **Nachher:** `MAX_NETWORK_WAIT=120` (10 Minuten bei 5 Sekunden pro Versuch)

#### Änderung 2: Direkte Prüfung der benötigten Dateien
Neue Variablen hinzugefügt:
```batch
set REQUIRED_FILE1=\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx
set REQUIRED_FILE2=\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx
```

#### Änderung 3: Erweiterte Verfügbarkeitsprüfung
Die Batch-Datei prüft jetzt in dieser Reihenfolge:
1. Ist das Root-Verzeichnis der Netzwerkfreigabe verfügbar?
2. Ist die Datei `Instrumente.xlsx` verfügbar?
3. Ist die Datei `bookings.xlsx` verfügbar?

Bei jedem Fehlschlag wartet das Script 5 Sekunden und versucht es erneut, bis die maximale Anzahl an Versuchen (120) erreicht ist.

#### Änderung 4: Verbesserte Log-Ausgaben
```batch
echo [%DATE% %TIME%] All required files are accessible >> "%LOG_FILE%"
```

## Vorteile der Änderungen

1. **Höhere Zuverlässigkeit:** Wartet bis zu 10 Minuten statt nur 5 Minuten
2. **Präzise Prüfung:** Stellt sicher, dass die tatsächlich benötigten Dateien verfügbar sind
3. **Bessere Diagnose:** Detaillierte Log-Meldungen zeigen genau, welche Datei fehlt
4. **Vermeidung von Exit Code 2:** Python-Script startet erst, wenn alle Voraussetzungen erfüllt sind

## Undo-Anleitung

Falls die Änderungen rückgängig gemacht werden sollen:

### Option 1: Über Kommandozeile (PowerShell als Administrator)
```powershell
# Backup überprüfen
Test-Path "D:\Dataserver\_Batchprozesse\status\start_status.bat.backup_2025-10-17"

# Aktuelles File sichern (optional)
Copy-Item "D:\Dataserver\_Batchprozesse\status\start_status.bat" "D:\Dataserver\_Batchprozesse\status\start_status.bat.new_version"

# Backup wiederherstellen
Copy-Item "D:\Dataserver\_Batchprozesse\status\start_status.bat.backup_2025-10-17" "D:\Dataserver\_Batchprozesse\status\start_status.bat" -Force
```

### Option 2: Über Windows Explorer
1. Navigieren Sie zu: `D:\Dataserver\_Batchprozesse\status\`
2. Löschen oder umbenennen Sie die Datei `start_status.bat`
3. Kopieren Sie `start_status.bat.backup_2025-10-17`
4. Benennen Sie die Kopie in `start_status.bat` um

### Option 3: Über cmd (Command Prompt als Administrator)
```cmd
cd /d "D:\Dataserver\_Batchprozesse\status"
copy start_status.bat start_status.bat.new_version
copy /Y start_status.bat.backup_2025-10-17 start_status.bat
```

## Test-Empfehlung

Um zu testen, ob die Änderungen funktionieren:

1. **Manueller Test:**
   ```cmd
   cd /d "D:\Dataserver\_Batchprozesse\status"
   start_status.bat
   ```
   Prüfen Sie dann `task_scheduler.log` auf die neuen Log-Meldungen.

2. **Server-Neustart-Test:**
   - Starten Sie den Server neu
   - Warten Sie 15 Minuten
   - Prüfen Sie `task_scheduler.log` auf erfolgreichen Start
   - Prüfen Sie den Task Scheduler Verlauf auf Exit Code 0 (Erfolg)

## Weitere Empfehlungen

Falls das Problem weiterhin auftritt, können folgende zusätzliche Maßnahmen ergriffen werden:

1. **Task Scheduler Verzögerung:**
   - Öffnen Sie Task Scheduler
   - Bearbeiten Sie den Task für `start_status.bat`
   - Fügen Sie eine Verzögerung von 2-3 Minuten nach dem Start hinzu

2. **Service Account Berechtigungen:**
   - Stellen Sie sicher, dass der Service Account Leserechte auf `\\WIN-H7BKO5H0RMC\Dataserver\` hat
   - Testen Sie den Zugriff manuell mit dem Service Account

3. **Netzwerk-Diagnose:**
   - Prüfen Sie die Windows Event Logs für Netzwerk-Events beim Systemstart
   - Stellen Sie sicher, dass der Netzwerkdienst vor dem Task Scheduler startet

## Geänderte Dateien

- `start_status.bat` (modifiziert)
- `start_status.bat.backup_2025-10-17` (neu erstellt)
- `CHANGELOG_2025-10-17.md` (dieses Dokument)

## Autor

Claude Code - 2025-10-17

## Referenzen

- Issue: Exit Code 2 nach Server-Neustart
- Logfile: `D:\Dataserver\_Batchprozesse\status\task_scheduler.log`
- Fehlerzeit: 2025-10-17 15:37:16 (Server-Neustart)
- Fehlerzeit: 2025-10-17 16:08:04 (Python-Script Fehler)
