# Fehler-Benachrichtigung im Projekt Status – Dokumentation

## Kontext

Dieses Dokument beschreibt die Integration des PowerShell-Benachrichtigungssystems
in das Projekt Status. Die Implementierung erfolgte am 2026-03-28 basierend auf den
Erfahrungen aus dem Projekt Depot (siehe `../depot/startscript_fehlermeldung_depot.md`).

## Architektur (Option B – autonom pro Projekt)

Jedes Projektverzeichnis enthaelt seine eigene Kopie der Benachrichtigungsdateien:
- `Send-ErrorNotification.ps1`  – Bibliothek mit Email- und Telegram-Funktionen
- `notify_config.json`          – Credentials (NICHT im Git-Repo, nur lokal)

## Projektstruktur Status

| Datei | Beschreibung |
|---|---|
| `app.py` | Flask Web Application (Dauerläufer) |
| `status.py` | Stock Monitoring Service (Dauerläufer) |
| `status_dsl.py` | DSL Speedtest Monitoring Service (Dauerläufer) |
| `start_app.ps1` | PowerShell-Wrapper für app.py |
| `start_status.ps1` | PowerShell-Wrapper für status.py (mit Netzwerk-Wait-Logik) |
| `start_status_dsl.ps1` | PowerShell-Wrapper für status_dsl.py |
| `Send-ErrorNotification.ps1` | Notification-Bibliothek (Email + Telegram) |
| `notify_config.json` | Lokale Konfiguration mit Credentials (nicht committet) |
| `logs/app_YYYY-MM.log` | Monatlich rotierendes Logfile für app.py |
| `logs/status_YYYY-MM.log` | Monatlich rotierendes Logfile für status.py |
| `logs/status_dsl_YYYY-MM.log` | Monatlich rotierendes Logfile für status_dsl.py |

**Projektverzeichnis:** `D:\Dataserver\_Batchprozesse\status`
**UNC-Pfad (Task Scheduler):** `\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status`
**Python:** `.venv\Scripts\python.exe`

## Unterschied zu Depot

Im Projekt Depot laeuft `depot.py` einmal taeglich und beendet sich.
Im Projekt Status laufen alle drei Python-Skripte als **Endlosschleifen** (Dauerlaeufer).
Die Notification wird daher nur bei **unerwartetem Absturz** (RC != 0) gesendet –
nicht bei einem normalen, planmaessigen Beenden.

## Durchgefuehrte Aenderungen (2026-03-28)

### 1. Send-ErrorNotification.ps1 hinzugefuegt

Direkte Kopie aus `../depot/Send-ErrorNotification.ps1`. Generische Bibliothek,
keine Anpassungen noetig. Unterstuetzt Email (Gmail SMTP) und Telegram Bot.

### 2. notify_config.json erstellt (lokal, nicht committet)

Gleiche Konfiguration wie Depot und MyFitnessPal_Sync:
- Telegram aktiv (`notify_telegram: true`)
- Email deaktiviert (`notify_email: false`)
- Empfaenger: `leo@haunschild-family.de`, `ah@haunschild-family.de`
- Computername: `WIN-H7BKO5H0RMC`

### 3. .gitignore aktualisiert

`notify_config.json` in Abschnitt "Notification credentials" hinzugefuegt.

### 4. Aenderungen in start_app.ps1

**Dot-Sourcing nach den Pfadvariablen (nach $ERRORLOG):**
```powershell
$notifyAvailable = $false
$notifyLib = Join-Path $scriptDir "Send-ErrorNotification.ps1"
if (Test-Path $notifyLib) {
    try {
        . $notifyLib
        $notifyAvailable = $true
    }
    catch { Write-Warning "FEHLER beim Laden der Notification-Bibliothek: $_" }
}
```

**Notification bei RC != 0 (nach dem Python-Aufruf):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_app (app.py)" -ExitCode $RC `
        -ErrorMessage "Flask application exited with code $RC" -LogFile $LOGFILE
}
```

**Notification im catch-Block (PowerShell-Exception):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_app (app.py)" -ExitCode $RC `
        -ErrorMessage $($_.Exception.Message) -LogFile $LOGFILE
}
```

### 5. Aenderungen in start_status.ps1

Dot-Sourcing identisch wie start_app.ps1 (siehe oben).

**Zusaetzliche Notification bei Netzwerk-Timeout:**
`start_status.ps1` enthaelt eine `Wait-ForNetworkResources`-Funktion, die bis zu
5 Minuten auf die Netzwerkfreigaben wartet. Bei Timeout wird jetzt ebenfalls
eine Notification gesendet:

```powershell
if (-not (Wait-ForNetworkResources -LogFile $LOGFILE -ErrorLog $ERRORLOG)) {
    if ($notifyAvailable) {
        Send-ErrorNotification -ScriptName "start_status (status.py)" -ExitCode 1 `
            -ErrorMessage "Netzwerk-Ressourcen nach Timeout nicht erreichbar" -LogFile $LOGFILE
    }
    exit 1
}
```

**Notification bei RC != 0 (nach dem Python-Aufruf):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_status (status.py)" -ExitCode $RC `
        -ErrorMessage "Python script exited with code $RC" -LogFile $LOGFILE
}
```

**Notification im catch-Block (PowerShell-Exception):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_status (status.py)" -ExitCode $RC `
        -ErrorMessage $($_.Exception.Message) -LogFile $LOGFILE
}
```

### 6. Aenderungen in start_status_dsl.ps1

Dot-Sourcing identisch wie start_app.ps1 (siehe oben).

**Notification bei RC != 0 (nach dem Python-Aufruf):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_status_dsl (status_dsl.py)" -ExitCode $RC `
        -ErrorMessage "DSL Speedtest script exited with code $RC" -LogFile $LOGFILE
}
```

**Notification im catch-Block (PowerShell-Exception):**
```powershell
if ($notifyAvailable) {
    Send-ErrorNotification -ScriptName "start_status_dsl (status_dsl.py)" -ExitCode $RC `
        -ErrorMessage $($_.Exception.Message) -LogFile $LOGFILE
}
```

## Wann wird eine Notification gesendet?

| Skript | Trigger |
|---|---|
| `start_app.ps1` | Flask (app.py) beendet sich mit RC != 0 |
| `start_app.ps1` | PowerShell-Exception im Wrapper |
| `start_status.ps1` | Netzwerk-Ressourcen nach 5 Min. Timeout nicht erreichbar |
| `start_status.ps1` | status.py beendet sich mit RC != 0 |
| `start_status.ps1` | PowerShell-Exception im Wrapper |
| `start_status_dsl.ps1` | status_dsl.py beendet sich mit RC != 0 |
| `start_status_dsl.ps1` | PowerShell-Exception im Wrapper |

**Kein Trigger bei:** Normalem Stopp via Task Scheduler (RC = 0).

## Hinweis: UNC-Pfad und $notifyLib

Die Status-Skripte verwenden `$scriptDir = "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"`
(hartkodierter UNC-Pfad, anders als Depot mit `$PSScriptRoot`).

`Join-Path $scriptDir "Send-ErrorNotification.ps1"` ergibt daher den UNC-Pfad
zur Bibliothek — das funktioniert korrekt unter dem SYSTEM-Konto im Task Scheduler.
Bei manueller Ausfuehrung als Administrator koennte der UNC-Pfad nicht erreichbar sein
(pre-existierendes Problem, nicht durch die Notification-Aenderungen verursacht).

### Notification manuell testen (Workaround bei UNC-Problem)

```powershell
cd "D:\Dataserver\_Batchprozesse\status"
. .\Send-ErrorNotification.ps1
Send-ErrorNotification -ScriptName "start_status" -ExitCode 1 -ErrorMessage "Das ist ein Test"
```

## notify_config.json Struktur (Referenz)

```json
{
  "smtp_server":        "smtp.gmail.com",
  "smtp_port":          587,
  "smtp_user":          "GMAIL_ADRESSE",
  "smtp_password":      "GMAIL_APP_PASSWORT",
  "from_address":       "GMAIL_ADRESSE",
  "to_addresses":       ["EMPFAENGER_1", "EMPFAENGER_2"],
  "telegram_bot_token": "BOT_TOKEN",
  "telegram_chat_id":   "CHAT_ID",
  "notify_email":       false,
  "notify_telegram":    true,
  "computername":       "WIN-H7BKO5H0RMC"
}
```

## Git-Commit

Folgende Dateien wurden committet:
- `Send-ErrorNotification.ps1` (neu, kopiert aus Depot)
- `start_app.ps1` (geaendert)
- `start_status.ps1` (geaendert)
- `start_status_dsl.ps1` (geaendert)
- `.gitignore` (geaendert, notify_config.json hinzugefuegt)
- `startscript_fehlermeldung_status.md` (neu)

`notify_config.json` ist **nicht** committet (in .gitignore).
