# CHANGELOG - 21. Mai 2026

## Zählerstand-Monitoring hinzugefügt

### Neue Funktion: Gas- und Stromzähler in der Statusseite

**Datum:** 21. Mai 2026  
**Entwicklung:** ahmain  
**Test & Deployment:** HauServer

---

### Übersicht

Die Statuswebseite zeigt nun die aktuellen Zählerstände von zwei lokalen Tasmota-Geräten an:

- **Gas:** Smartnetz Gas Reader (192.168.178.130) — Zählerstand in m³
- **Strom:** Hichi Lesekopf MT691 (192.168.178.133) — Bezug, Einspeisung und aktueller Verbrauch in kWh / W

---

### Neue Dateien

| Datei | Beschreibung |
|---|---|
| `status_zaehler.py` | Hintergrundskript — fragt alle 5 Minuten beide Tasmota-Geräte via HTTP ab und schreibt `static/zaehler.json` |
| `status_zaehler.ini` | Konfiguration — Tasmota-URLs, Logfile-Pfad, Refresh-Intervall |
| `start_status_zaehler.ps1` | PowerShell-Starter — analog zu `start_status_dsl.ps1` |

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `templates/main.html` | Neuer "Zählerstände"-Block mit Gas, Strom Bezug, Einspeisung, Aktueller Verbrauch (JS-Refresh alle 5 min) |
| `CLAUDE.md` | Dokumentation der neuen Komponenten und Task Scheduler Tasks |

---

### Technische Details

**Datenparsing:**  
Die Tasmota-Geräte liefern ihre Sensordaten über `/?m=1` im proprietären Template-Format (`{s}Label{m}Wert{e}`). Das Script parst die Rohdaten per Regex — ohne externe HTTP-Bibliothek (stdlib `urllib.request`).

**Ausgabe `static/zaehler.json`:**
```json
{
  "timestamp": "2026-05-21 19:25:45",
  "gas": { "zaehlerstand_m3": 8961.45 },
  "strom": {
    "bezug_kwh": 54855.0,
    "einspeisung_kwh": 20317.0,
    "aktuell_w": 0
  }
}
```

**Task Scheduler:**  
Task "Zaehler Monitoring" in `\AHSkripts\` wurde durch Klonen des bestehenden "DSL Speedtest Monitoring"-Tasks angelegt und läuft unter `HauServer\Service`.

---

### Bekanntes Problem: Flask-Template-Cache

Nach Änderungen an `templates/main.html` muss der "Status Web App"-Task neu gestartet werden, da Jinja2 Templates im Nicht-Debug-Modus cached:

```powershell
Stop-ScheduledTask -TaskName "Status Web App" -TaskPath "\AHSkripts\"
Start-ScheduledTask -TaskName "Status Web App" -TaskPath "\AHSkripts\"
```
