# Changelog - 2026-10-12

## Zusammenfassung

Drei Änderungen an einem Tag:

1. **Zählerstand-Monitoring:** Der Gaszähler (Smartnetz Gas Reader, 192.168.178.130) wurde stillgelegt und vollständig aus Code, Konfiguration und Dashboard entfernt. Der neue Smart Meter arbeitet mit einem Stromwandler (Faktor 20), alle Stromwerte werden jetzt entsprechend hochgerechnet.
2. **DSL-Speedtest:** Seit dem 30.09.2026 wurde fast nur noch gegen Server im Ausland gemessen (v. a. Warschau, 14 Mbit/s / 218 ms), weil der feste Wunsch-Server Telekom Frankfurt (ID 31448) bei Ookla nicht mehr existiert. Behoben durch neuen Wunsch-Server Telekom Stuttgart (ID 74184) und robustere Fallback-Logik.
3. **Speedtest-Historie bereinigt:** 1.532 Auslandsmessungen und 51 Messungen mit unplausiblem Ping (> 1.000 ms, bis 1.800.000 ms) aus `speedtest_data.parquet` entfernt. Neue Ausreißer werden künftig verworfen.

---

## 1. Zählerstand-Monitoring: Gaszähler entfernt, Wandlerfaktor Strom

### Ausgangslage

- Gaszähler seit 16.09.2026 15:10 nicht mehr erreichbar (Timeout), letzter Wert 9195,15 m³. Dashboard zeigte seitdem „--".
- Stromzähler getauscht: Bezug sprang von ~54.890 kWh auf 0 und stieg danach in 0,1-kWh-Schritten (34,4 kWh / Einspeisung 5,3 kWh am 12.10.). Der neue Smart Meter misst über einen Stromwandler mit Faktor 20 — die vom Hichi-Lesekopf gelesenen Rohwerte sind um diesen Faktor zu klein.

### Änderungen

- **`status_zaehler.py`:** `parse_gas()`, Gas-Abfrage und `gas`-Block in `zaehler.json` entfernt. Neue Einstellung `strom_faktor` wird gelesen (Default 1.0) und in `parse_strom()` auf **Bezug, Einspeisung und Aktuellen Verbrauch** angewendet (Ergebnisse auf 3 Nachkommastellen gerundet, um Float-Artefakte zu vermeiden). Faktor wird beim Start ins Log geschrieben.
- **`status_zaehler.ini`:** `gas_url` entfernt, `strom_faktor = 20` in `[Geraete]` ergänzt.
- **`templates/main.html`:** Kachel „Gas Zählerstand" und zugehöriges JavaScript entfernt.

### Verifikation

`static/zaehler.json` nach Neustart von „Zaehler Monitoring" und „Status Web App":
```json
"strom": { "bezug_kwh": 688.0, "einspeisung_kwh": 106.0, "aktuell_w": 0 }
```
(Rohwerte 34,4 / 5,3 kWh × 20). Ausgeliefertes HTML enthält keine Gas-Kachel mehr.

**Offen:** „Aktueller Verbrauch" liefert weiterhin 0 W (auch P1–P3) — der Zähler gibt die Momentanleistung vermutlich erst nach PIN-Freischaltung aus.

---

## 2. DSL-Speedtest: Messungen gegen Server im Ausland

### Symptom

Dashboard zeigte als Zielserver häufig Server im Ausland mit schlechten Werten, z. B. „SWEET TV – Warsaw, Poland", 14,23 Mbit/s Download, 218 ms Ping.

### Diagnose

Ablauf in `status_dsl.log` bei jedem Test seit dem **30.09.2026** (letzter erfolgreicher CLI-Test gegen ID 31448: 30.09.2026 13:31):

1. `speedtest.exe ... --secure` → `Unrecognized option: --secure` (Ookla CLI 1.2.0.84 kennt die Option nicht — schlug schon immer fehl, war aber harmlos)
2. `speedtest.exe ... --server-id 31448` → `No servers defined (NoServersException)` — **Server Telekom Frankfurt existiert bei Ookla nicht mehr**
3. Fallback auf Python-Lib `speedtest-cli 2.1.3`: Server-ID nicht gefunden (`NoMatchedServers`), Filter Telekom/Frankfurt findet nichts
4. Fallback `get_best_server()` → Warschau

**Root Cause für das Ausland:** Die nicht mehr gepflegte Python-Lib `speedtest-cli 2.1.3` erhält über die Legacy-API von Ookla nur noch **10 Server, alle in Polen** — obwohl der Client korrekt als DE / Deutsche Telekom erkannt wird. Jeder Fallback auf die Python-Lib landet daher zwangsläufig im Ausland.

Die Ookla-CLI selbst liefert dagegen korrekt nahe Server (`speedtest.exe --servers`): Telekom Stuttgart (74184), imos Göppingen, indasys Stuttgart, …

### Änderungen

- **`status_dsl.ini`:** `server_id = 74184` (Deutsche Telekom Stuttgart), `city = Stuttgart`, Hinweis auf `speedtest.exe --servers` im Kommentar.
- **`status_dsl.py` – `perform_speedtest_cli()`:**
  - Erst Wunsch-Server, bei Fehlschlag **Ookla-Auto-Auswahl** (ohne `--server-id`) — die CLI wählt zuverlässig nahe Server, bevor überhaupt auf die Python-Lib zurückgefallen wird.
  - Nicht unterstützte Option `--secure` entfernt (spart einen garantiert fehlschlagenden Aufruf pro Messung).
- **`status_dsl.py` – `perform_speedtest_py()`:**
  - Filter wird schrittweise gelockert: Sponsor+Stadt+Land → Sponsor+Land → nur Land.
  - Ist kein Server im konfigurierten Land verfügbar, wird die Messung **übersprungen** statt gegen einen Server im Ausland gemessen (`get_best_server()` nur noch, wenn kein `country` konfiguriert ist).
- **Code-Defaults** von 31448/Frankfurt auf 74184/Stuttgart aktualisiert.

### Verifikation

- CLI-Test mit alter ID 31448: Fallback auf Auto-Auswahl → Telekom Stuttgart, 340 / 76 Mbit/s, 17 ms.
- Nach Neustart des Tasks: `Deutsche Telekom – Stuttgart, Germany (ID 74184)`, 344 / 77 Mbit/s, 16 ms.

---

## 3. Speedtest-Historie bereinigt + Plausibilitätsprüfung Ping

### Bereinigung `speedtest_data.parquet`

Task „DSL Speedtest Monitoring" während der Bereinigung gestoppt (kein gleichzeitiger Schreibzugriff).

| Schritt | Backup | Entfernt | Danach |
|---|---|---|---|
| Auslandsmessungen (`server_location` ohne „Germany") | `_Archiv\speedtest_data.parquet.backup_2026-10-12` | 1.532 (06.09.2025 – 12.10.2026; u. a. Schweiz 208, Italien 178, Polen 173, Niederlande 129, UK 112) | 35.086 |
| Ping > 1.000 ms | `_Archiv\speedtest_data.parquet.backup_2026-10-12_vor_ping_filter` | 51 (Werte bis 1.800.000 ms) | 35.036 |

Ping-Durchschnitt danach: **21 ms** (vorher 1.373 ms), Median 19 ms. Werte zwischen 200 und 1.000 ms wurden bewusst behalten — sie treten meist zusammen mit eingebrochenem Download auf und sind vermutlich echte Störungen.

Hinweis: `speedtest_data.parquet` und die Backups sind per `.gitignore` nicht versioniert — Bereinigung nur lokal auf dem Server.

### Plausibilitätsprüfung

- **`status_dsl.ini`:** neue Einstellung `max_ping_ms = 1000` in `[Speedtest]`.
- **`status_dsl.py` – `run_single_speedtest()`:** Ergebnisse mit Ping über `max_ping_ms` werden als `WARN: Unplausibler Ping … – Messung verworfen` geloggt und weder in `speedtest.json` noch in die Parquet-Historie geschrieben.

---

## Geänderte/Neue Dateien

- **NEU:** `CHANGELOG_2026-10-12.md` (dieses Dokument)
- **GEÄNDERT:** `CHANGELOG.md` (Master), `CLAUDE.md`
- **GEÄNDERT:** `status_zaehler.py`, `status_zaehler.ini`, `templates/main.html`, `start_status_zaehler.ps1` (Kommentar)
- **GEÄNDERT:** `status_dsl.py`, `status_dsl.ini`
- **DATEN (nicht versioniert):** `speedtest_data.parquet` bereinigt, zwei Backups in `_Archiv\`
- **System:** Tasks „Zaehler Monitoring", „Status Web App" und „DSL Speedtest Monitoring" neu gestartet

## Commits

- `c5253bf` Remove decommissioned gas meter and apply current-transformer factor to electricity values
- `5c64f8c` Fix DSL speedtest measuring against foreign servers
- `bd968d0` Discard speedtest results with implausible ping values

## Referenzen

- **Verwandte Dokumente:** `CLAUDE.md`, `CHANGELOG_2026-05-21.md` (Einführung Zählerstand-Monitoring)
- **Server-Liste prüfen:** `ookla\speedtest.exe --accept-license --accept-gdpr --servers`
