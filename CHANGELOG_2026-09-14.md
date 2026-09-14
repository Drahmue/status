# Changelog - 2026-09-14

## Zusammenfassung

Auf dem Web-Dashboard wurden nur noch 3 von ~11 Portfolio-Positionen (BASF, Münchener Rückv., Bitcoin) angezeigt. Ursache war kein Problem des Datenanbieters (yfinance/Yahoo Finance lieferte auf Anfrage sofort und vollständig Kurse für alle Ticker), sondern eine über Wochen degradierte, seit dem 23.08.2026 ununterbrochen laufende Prozess-Instanz des Stock Monitoring Service in Kombination mit fehlendem Error-Logging.

## Symptom

Dashboard zeigte nur BASF, Muenchener Rueckv und Bitcoin in Euro an, obwohl das Depot laut `Instrumente.xlsx`/`bookings.xlsx` ca. 11 aktive Positionen mit gültigem Ticker und Bestand > 0 umfasst (u. a. VGEU/A1T8FS, EUNL/A0RPWH, XMME/A12GVR, EUN4/A0RGEN, Xetra-Gold/A0S9GB, IB26/A3D8E3, CEBD/A3EFXB, EXSH/263529).

## Diagnose

Geprüft und als Ursache ausgeschlossen:
- **yfinance/Yahoo Finance:** Manueller Test aller 20 Ticker aus `Instrumente.xlsx` lieferte sofort für jeden Ticker einen aktuellen Kurs — kein Ausfall des Datenanbieters.
- **Portfoliodaten:** Frisches Neuberechnen von `shares_from_bookings()` mit den aktuellen Excel-Dateien bestätigte ~11 Positionen mit Bestand > 0 zum Referenztag 11.09.2026 — die fehlenden Positionen sind langjährige Sparplan-Bestände (teils seit 2022/2023), keine kürzlich hinzugekommenen.
- **status.log:** Keinerlei WARNING/ERROR-Einträge im relevanten Zeitraum, obwohl der Fehler offensichtlich vorlag.

Root Cause gefunden:
- Der Python-Prozess (`status.py`) lief seit dem 23.08.2026 19:57 ununterbrochen (Task Scheduler `State: Running`, kein Neustart) — seit dem `ExecutionTimeLimit=PT0S`-Fix (siehe CHANGELOG_2026-02-27.md) läuft er ohne automatisches 72h-Limit weiter.
- Über den mehrwöchigen Dauerbetrieb mit minütlicher sequentieller `yfinance`-Abfrage degradierte vermutlich die interne yfinance-Session/-Cookie ("crumb"), sodass in den einzelnen 60-Sekunden-Zyklen die meisten Ticker-Abrufe fehlschlugen — mal waren nur wenige Ticker erfolgreich.
- **Zusätzliches Problem:** `get_current_prices()` in `status.py` fing Fehler pro Ticker nur mit `print()` ab, nicht mit `screen_and_log()`. Bei einem per Task Scheduler gestarteten Service ohne angehängte Konsole gehen `print()`-Ausgaben ins Leere — die Fehlschläge waren daher im Log komplett unsichtbar und der Vorfall nicht diagnostizierbar.

## Fix

**Sofortmaßnahme:** Task „Stock Monitoring Service" gestoppt und neu gestartet → frische yfinance-Session, danach sofort wieder alle 11 Positionen im Dashboard sichtbar.

**Code-Fix** in `get_current_prices()` (`status.py`):
- Jeder fehlgeschlagene Ticker-Abruf (Exception, leere Antwort, leere Close-Serie) wird jetzt als `WARNING` über `screen_and_log()` ins `status.log` geschrieben.
- Zusätzliche Zusammenfassungszeile pro Zyklus bei unvollständigem Abruf: `Kursabfrage unvollständig: X/Y Ticker erfolgreich abgerufen.`
- Verifiziert mit einem bewusst ungültigen Test-Ticker — Warnung erscheint korrekt im Log.

**Bewusst nicht umgesetzt:** Täglicher automatischer Neustart des Service, um der Session-Degradation präventiv vorzubeugen — auf ausdrücklichen Wunsch nicht eingerichtet. Bei erneutem Auftreten ist der Vorfall dank des Logging-Fixes jetzt aber im `status.log` nachvollziehbar (WARNING-Einträge statt Stille).

## Verifikation

- Nach Neustart: `static/depotdaten.json` enthält wieder 11 Positionen + Summe (vorher 3 + Summe).
- Logging-Fix mit synthetischem Fehlversuch getestet: `WARNING`-Zeilen erscheinen korrekt in `status.log`.
- Service nach Einspielen des Fixes erneut neu gestartet, läuft seither fehlerfrei.

## Geänderte/Neue Dateien

- **NEU:** `CHANGELOG_2026-09-14.md` (dieses Dokument)
- **GEÄNDERT:** `CHANGELOG.md` (Master) — Eintrag in Changelog-Übersicht ergänzt
- **GEÄNDERT:** `status.py` — `get_current_prices()`: Per-Ticker-Fehler werden jetzt geloggt statt nur `print()`-ausgegeben; Zusammenfassungszeile bei unvollständigem Abruf
- **System:** Task „Stock Monitoring Service" zweimal neu gestartet (Sofortmaßnahme + nach Fix)

## Referenzen

- **Verwandte Dokumente:** `CLAUDE.md`, `Stock_Monitoring_Service_Analyse.md`, `TROUBLESHOOTING_STOCK_MONITORING.md`, `CHANGELOG_2026-02-27.md` (ExecutionTimeLimit-Fix, Vorbedingung für dieses Problem)
