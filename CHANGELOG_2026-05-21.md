# CHANGELOG - 21. Mai 2026

## Responsive Design für alle Geräte

### Neue Funktion: Statusseite passt sich automatisch an Bildschirmgröße an

**Datum:** 22. Mai 2026  
**Geänderte Datei:** `templates/main.html`

---

### Übersicht

Die Statusseite skaliert nun automatisch abhängig vom Gerät — Desktop, Tablet, Smartphone und Samsung Galaxy Z Fold (zugeklappt und aufgeklappt).

---

### Breakpoints

| Gerät | Breakpoint | Schriftgröße | Besonderheiten |
|-------|-----------|-------------|----------------|
| Desktop | > 820px | 2em | Unverändert |
| Tablet / Z Fold aufgeklappt (~748px) | ≤ 820px | 1.4em | Kompakteres Padding |
| Smartphone / Z Fold zugeklappt (~390px) | ≤ 430px | 1.0em | Tabelle horizontal scrollbar |

---

### Technische Änderungen

- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` ergänzt — verhindert künstliches Herauszoomen auf mobilen Browsern
- CSS Media Queries für drei Bildschirmgrößen hinzugefügt
- Depot-Tabelle in `<div class="table-wrapper">` eingeschlossen mit `overflow-x: auto` — bei schmalen Screens horizontal scrollbar statt abgeschnitten
- Samsung Galaxy Z Fold wird automatisch erkannt: zugeklappt (Cover Screen) springt in ≤ 430px-Modus, aufgeklappt (Innendisplay) in ≤ 820px-Modus

---

## Externer Zugriff via Tailscale eingerichtet

### Neue Funktion: Statusseite von eigenen Geräten außerhalb des Heimnetzes erreichbar

**Datum:** 21. Mai 2026  
**Eingerichtet auf:** HauServer, ahflipalt, ahfold, ahlap

---

### Übersicht

Die Statusseite ist nun von den eigenen Geräten auch außerhalb des Heimnetzes erreichbar — ohne offene Router-Ports und ohne Sicherheitsrisiken.

**Lösung:** [Tailscale](https://tailscale.com) bildet ein privates VPN-Mesh zwischen den eigenen Geräten. Nur Geräte, die mit demselben Tailscale-Account eingeloggt sind, können sich gegenseitig erreichen.

---

### Zugriff

Wenn Tailscale auf dem jeweiligen Gerät aktiv ist:

```
http://hauserver:5000
```

Alternativ über die Tailscale-IP des Servers (z. B. `100.x.x.x:5000`), falls MagicDNS nicht verfügbar ist.

**Voraussetzung:** Tailscale muss auf dem zugreifenden Gerät laufen und mit demselben Account eingeloggt sein.

---

### Eingerichtete Geräte

| Gerät | Typ | Installation |
|-------|-----|-------------|
| HauServer | Windows Server 2022 | `winget install Tailscale.Tailscale` |
| ahflipalt | Windows | `winget install Tailscale.Tailscale` |
| ahlap | Windows | `winget install Tailscale.Tailscale` |
| ahfold | Android | Play Store → "Tailscale" |

Alle Geräte sind mit demselben Tailscale-Account verknüpft.

---

### Technische Details

- **Kein Port-Forwarding** am Router erforderlich
- **Kein offener Port** von außen sichtbar
- Der Server baut eine ausgehende Verbindung zu Tailscale auf — externe Geräte verbinden sich über das Tailscale-Netz, nicht direkt
- **MagicDNS** ermöglicht den Hostnamen `hauserver` statt IP-Adresse
- **Kostenlos** für Personal-Plan (1 Nutzer, bis 100 Geräte)
- Flask läuft unverändert auf `localhost:5000` — keine Konfigurationsänderung am Server nötig

---

### Tailscale-Dienst auf HauServer

Tailscale läuft als Windows-Dienst und startet automatisch mit dem System:

```powershell
# Status prüfen
Get-Service -Name Tailscale

# Tailscale-IP des Servers anzeigen
tailscale ip
```

---

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
