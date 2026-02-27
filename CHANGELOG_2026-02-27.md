# Changelog - 2026-02-27

## Zusammenfassung

Zwei Stabilitätsprobleme im Stock Monitoring Service identifiziert und behoben:
1. Task Scheduler `ExecutionTimeLimit` beendete den Daemon-Prozess nach exakt 72 Stunden
2. Fehlende Fehlerbehandlung in der Monitoring-Schleife führte bei unbehandelten Exceptions zu lautlosen Abstürzen

## Hintergrund / Diagnose

Der Stock Monitoring Service stoppte wiederholt nach ~72 Stunden ohne jegliche Fehlermeldung:
- 25.11.2025 gestartet → 28.11.2025 gestoppt (71h 58m)
- 15.02.2026 gestartet → 18.02.2026 gestoppt (71h 58m)
- 22.02.2026 gestartet → 25.02.2026 gestoppt (71h 58m)

Das exakte 72h-Muster und Exit Code `267014` führten zur Identifikation des `ExecutionTimeLimit`-Problems.

## Durchgeführte Änderungen

### 1. Task Scheduler: ExecutionTimeLimit entfernt

**Betroffene Task:** `\AHSkripts\Stock Monitoring Service`

**Problem:** Der Task war mit dem Standard-Wert `PT72H` (72 Stunden) konfiguriert. Nach Ablauf dieser Zeit beendet Windows den Prozess zwangsweise – ohne Warnung und ohne Log-Eintrag. Exit Code `267014` ist der offizielle Windows-Code für dieses Ereignis.

**Lösung:** `ExecutionTimeLimit` auf `PT0S` gesetzt (kein Limit).

```powershell
$task = Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
$task.Settings.ExecutionTimeLimit = "PT0S"
Set-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" `
    -Settings $task.Settings -User "WIN-H7BKO5H0RMC\Service" -Password $pw
```

**Prüfung der anderen Tasks:** DSL Speedtest Monitoring und Status Web App hatten bereits `PT0S` – kein Handlungsbedarf.

### 2. status.py: Fehlerbehandlung in run_monitor() ergänzt

**Datei:** `status.py`

**Problem:** Die `while True`-Schleife in `run_monitor()` hatte keinen äußeren `try/except`-Block. Unbehandelte Exceptions (z.B. yfinance-Netzwerkfehler, API-Timeouts) beendeten das Python-Script sofort und lautlos – kein Fehler-Log, kein Traceback.

Folgende Stellen konnten eine unbehandelte Exception auslösen:
- `get_last_trading_day()` (Zeile 402)
- `get_current_prices(instruments_df)` (Zeile 428)
- `get_reference_values_from_yfinance(...)` (Zeile 431)
- `pd.DataFrame(output_rows)` (Zeile 477)
- `open("static/depotdaten.json", 'w', ...)` (Zeile 508)

**Lösung:** Zwei Änderungen in `status.py`:

1. `import traceback` hinzugefügt (Zeile 8)
2. Schleifenkörper in `try/except` eingewickelt:

```python
while True:
    refresh_time = settings.get("Timing", {}).get("refresh_time", 60)
    try:
        # ... gesamter bisheriger Schleifenkörper ...
        time.sleep(refresh_time)
    except Exception as e:
        screen_and_log(
            f"ERROR: Unbehandelte Exception in Monitoring-Schleife: {e}\n{traceback.format_exc()}",
            logfile
        )
        screen_and_log(
            f"Schleife wird nach {refresh_time} Sekunden fortgesetzt.",
            logfile
        )
        time.sleep(refresh_time)
```

**Verhalten nach der Änderung:**
- Exceptions werden mit vollem Traceback in `status.log` geloggt
- Die Monitoring-Schleife läuft nach einem Fehler automatisch weiter
- `refresh_time` vor den `try`-Block gezogen, damit es im `except`-Block verfügbar ist

## Betroffene Dateien

| Datei | Art der Änderung |
|-------|-----------------|
| `status.py` | `import traceback` + try/except in `run_monitor()` |
| `TROUBLESHOOTING_STOCK_MONITORING.md` | Ursachen und Lösungen dokumentiert |
| `CLAUDE.md` | Known Issues aktualisiert |

## Nicht betroffene Komponenten

- `status_dsl.py` – DSL Speedtest Monitoring (separates Script)
- `app.py` – Flask Web App
- `start_status.ps1` – PowerShell Starter (keine Änderung)
- Task Scheduler: DSL Speedtest Monitoring, Status Web App (bereits PT0S)
