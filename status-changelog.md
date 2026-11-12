# status – Changelog

## 2026-11-12 – Startskripte schreiben zeilenweise ins Log (datahub DH-063)

- `start_status.ps1`, `start_app.ps1`, `start_status_dsl.ps1` und `start_status_zaehler.ps1` rufen Python jetzt über `_shared\Invoke-Logged.psm1 -Mode Stream` auf. Jede Zeile von stdout und stderr steht sofort mit Zeitstempel im Monatslog `logs\<name>_yyyy-MM.log`. Vorher wurde alles bis zum Prozessende in `$pythonResult` gepuffert, und beim Stoppen ging es verloren. Fehlt der Helfer, läuft der alte Aufruf.
- Die 4 Tasks wurden am 12.11. zwischen 17:16 und 17:18 nach OK von AH neu gestartet. Die Startlogs füllen sich sofort, Web-App HTTP 200, die JSON-Dateien sind aktuell.
- Hinweis: Ältere Teile der Monatslogs stammen von `Add-Content` (unter PS 5.1 ANSI), neue Zeilen sind UTF-8. Ab Dezember ist die Datei einheitlich.

## 2026-11-12 – status.py: Handle- und Speicherleck behoben (datahub DH-056)

- **Befund:** 18 h nach dem Neustart am 11.11. hatte `status.py` 419 MB belegt (+280 MB pro Tag) und 180.456 Handles offen.
  - `yf.download` startet je Aufruf Threads über `multitasking` 0.0.12. Diese Bibliothek hängt jeden Thread an `config["TASKS"]` an und entfernt ihn nie. Ergebnis: +290 bis +380 Handles je Runde. Mit `threads=False` sind es ±0, gemessen in Testrunden ohne Schreiben.
  - Eine Runde machte 152 `yf.download`. 121 davon entfielen auf den Monatsvergleich, weil er in der Schleife für jede WKN neu für alle WKN abgerufen wurde.
- **Geändert in `status.py`:**
  - A: `threads=False` in beiden `yf.download`.
  - B: Die Referenzkurse für Vortag und Vormonat liegen in einem Zwischenspeicher je (wkn, Stichtag). Gespeichert werden nur exakte Treffer. Ersatzkurse, also wenn der Stichtag bei yfinance noch fehlt, werden in jeder Runde neu abgefragt. Der Zwischenspeicher hält nur die aktuellen Stichtage. Den Monatsvergleich berechnet der Code jetzt einmal je Runde. Neue Hilfsfunktion `_historical_price` liefert (Preis, exakt). `get_historical_price` und die Signaturen bleiben gleich.
  - C: Die Tabelle wird nicht mehr in jeder Runde ausgegeben, sie steht in `depotdaten.json`.
- **Test:** Die echte `run_monitor` lief 4 Runden im Testordner. Runde 1 machte 42 Abrufe, danach 20 je Runde. Die Handles blieben stabil. Keine Ausgabe, `depotdaten.json` gleich aufgebaut, Monatsvergleich 11/11, der Zwischenspeicher stimmt mit dem direkten Abruf überein. Den Ersatzfall habe ich offline mit Testdaten geprüft.
- **Betrieb:** Neustart des `Stock Monitoring Service` am 12.11. um 15:49 nach OK von AH, Commit `e1cd736`. In 5 Runden blieben die Handles bei 538 bis 543 und der Speicher bei 197 MB. Eine Runde dauert etwa 63 statt 70 s.
- Offen in DH-063 (datahub): Die Startskripte puffern stdout bis Prozessende, die Ausgabe gehört zeilenweise ins Monatslog.

## 2026-11-12 – DSL-Speedtest: Ookla-Limit, Intervall 30 Min., Meldung bei Ausfall (datahub DH-051)

- **Befund im Log:** Bis zum 29.10. gab es 138 CLI-Messungen am Tag, 6 pro Stunde. Seit dem 30.10. antwortet die Ookla-CLI oft mit `rc=429 Limit reached`. Erfolgreich sind nur noch etwa 2 bis 3 pro Stunde, im Abstand von 20 bis 31 Minuten.
  - Am 11.11. gab es 140 Zyklen und 51 CLI-Messungen. 55 Ersatzmessungen über die Python-Lib liefen gegen **Telefónica Berlin**, weil ihre alte Serverliste keinen Telekom-Server enthält. 34 Messungen fehlten ganz.
  - Bei 429 hat die CLI sofort noch einen zweiten Server versucht, das war zwecklos.
- **Geändert in `status_dsl.py`:**
  - Bei `rc=429` wird die Messung ausgelassen (Rückgabe `LIMIT_REACHED`), ohne zweiten Server und ohne Ersatzmessung (Entscheidung AH). Bei anderen CLI-Fehlern springt die Python-Lib weiter ein.
  - Neu ist `[Monitoring] alarm_hours = 3`: Gibt es so lange keine erfolgreiche Messung, kommt einmal eine Telegram-Warnung über `_shared\notify_telegram`, mit der nächsten Messung eine Entwarnung.
- **`status_dsl.ini`:** `refresh_time` 600 → 1800 (Entscheidung AH).
- **Test:** Offline mit ersetzter CLI, Telegram und Uhr, 6/6 OK. Der Task `DSL Speedtest Monitoring` wurde nach OK von AH um 13:34 neu gestartet. Der erste Versuch lief ins Limit, weil die letzte Messung um 13:27 erst 7 Minuten zurücklag, und wurde wie vorgesehen ausgelassen. Commit `69ff8e1`, gepusht.
- Hinweis: Die Messreihe enthält vom 30.10. bis 12.11. Messungen gegen Telefónica Berlin (`server_name` „Telefónica Germany …“). Für Auswertungen lassen sie sich über `server_name` herausfiltern.

## 2026-11-11 – Stückzahlen aus shares_day.xlsx (datahub DH-050), Neustart wegen Speicher (DH-056)

- Anlass: `status.py` hat die Stückzahlen nur beim Start aus `bookings.xlsx` berechnet, und zwar nur bis Start + 30 Tage. Der Dienst lief seit dem 24.10. ohne Neustart. Neue Buchungen kamen deshalb nicht an, und nach 30 Tagen hätten die Stückzahlen ganz gefehlt.
- Neu: Die Klasse `SharesDaySource` liest `D:\Dataserver\Dummy\Finance_Output\shares_day.xlsx`. Diese Datei berechnet depot (Task `Depot Script Daily Fixed`) täglich um 05:00 mit denselben Funktionen `shares_from_bookings` und `aggregate_banks`. Die Monitoring-Schleife prüft in jeder Runde den Zeitstempel der Datei. Ist die Datei neu und seit mindestens 120 s unverändert, liest `status.py` sie ein, ohne dass ein Neustart nötig ist. Wenn das Lesen scheitert, bleibt der bisherige Stand stehen, und das Log bekommt eine Warnung (einmal je Dateistand). Fehlt ein Tag, gilt die letzte Zeile davor, denn die Datei endet am letzten Kurstag. Ist die Datei älter als `shares_day_max_age_hours`, steht eine Warnung im Log.
- `main()` importiert die Buchungen nicht mehr. Die Buchungsfunktionen bleiben nur für die Testskripte `test_*.py`. Die Startprüfung `required_files` umfasst jetzt `Instrumente.xlsx` und `shares_day.xlsx`.
- `status.ini`: In `[Files]` ist `shares_day` neu, in `[Timing]` `shares_day_max_age_hours = 30`. `bookings` bleibt mit dem Kommentar „nur Testskripte“.
- Geprüft: Die alte Berechnung und die xlsx stimmen überein (32 WKN, 1442 Tage, 0 abweichende Zellen). 15 Funktionstests von `SharesDaySource` liefen auf einer Kopie der Datei, darunter Nachladen, eine frisch geschriebene Datei, eine defekte Datei, eine fehlende Datei und eine veraltete Datei. Die Warnungstexte habe ich dabei nicht im Log gesehen, geprüft ist nur der Codepfad.
- Der Dienst wurde am 11.11. zweimal neu gestartet. Um 21:33 lief noch der alte Code, der Neustart diente dem Speicher (vorher 7,3 GB, DH-056). Um 21:38 startete der neue Code. Im Log steht `shares_day geladen: 32 WKN, 30.11.2022-10.11.2026, Datei vom 11.11.2026 05:01`. Commit `aca3a15` ist gepusht, nach einem Rebase auf `dbdf2a0` und `eda3833`, die nur Doku betreffen.
- Doku nachgezogen: `CLAUDE.md`, `DEPLOYMENT.md`, `TROUBLESHOOTING_STOCK_MONITORING.md` und `CHANGELOG.md` (Abschnitt 5.5) nennen jetzt `shares_day.xlsx` als Quelle.
- 12.11.: ST-02 erledigt. depot schrieb die Datei um 05:01:10, status hat sie um 05:04:15 ohne Neustart nachgeladen. Der Speicher liegt bei 49 MB. ST-03 (AHMAIN-Pull) angelegt.

Verworfene Ansätze:
- Die 30-Tage-Grenze einfach erhöhen oder die Buchungen täglich neu einlesen: Die Berechnung gäbe es dann doppelt, in depot und in status, und sie könnte auseinanderlaufen.

## 2026-10-23 – Lokal mit Repo abgeglichen, CLAUDE.md auf HauServer umgestellt

- Lokal mit `origin/main` verglichen: Lokal war 21 Commits hinter dem Remote und hatte keine eigenen Commits. Dazu kamen 3 Änderungen, die nicht committet waren.
- Die lokalen Änderungen an `status.ini` (UNC-Pfade `\\HauServer\...`) und `Setup-TaskScheduler-Fixed.ps1` (ServiceAccount `HauServer\Service`) verworfen. Der Remote hat beides schon anders gelöst: In `status.ini` stehen lokale `D:\`-Pfade, und das Setup-Skript ist gelöscht.
- Die Änderung an `Status 20250901.docx` verworfen.
- `git pull --ff-only`: alle 21 Commits übernommen, ohne Konflikte.
- `CLAUDE.md`: Den Pfad zur Standardbibliothek und den Service-User im Task-Scheduler-Beispiel auf `HauServer` umgestellt. Die Excel-Quellen `Instrumente.xlsx` und `bookings.xlsx` haben jetzt dieselben `D:\Dataserver\Dummy\Finance_Input\...`-Pfade wie `status.ini`. Committet und gepusht (`d807ed5`).

- ST-01 erledigt: In `DEPLOYMENT.md`, `TROUBLESHOOTING_STOCK_MONITORING.md`, `startscript_fehlermeldung_status.md` und `CHANGELOG.md` steht jetzt `HauServer` statt `WIN-H7BKO5H0RMC`. Pfade auf `\\WIN-H7BKO5H0RMC\Dataserver` sind jetzt lokale `D:\Dataserver`-Pfade, so wie in den Start-Skripten. Die Standardbibliothek und der UNC-Hinweis verweisen auf `\\HauServer\...`. Den veralteten Abschnitt zu `$scriptDir` in `startscript_fehlermeldung_status.md` habe ich als „überholt“ markiert, weil die Skripte inzwischen `$PSScriptRoot` verwenden.

Verworfene Ansätze:
- Lokale Änderungen per `git stash` aufheben: nicht nötig, weil der Remote dieselben Punkte schon gelöst hatte.
- Excel-Quellen in `CLAUDE.md` als `\\HauServer\...`: Stattdessen die `D:\`-Pfade genommen, damit die Doku zu `status.ini` passt.
