# status – Session 2026-11-12 (aus datahub, HauServer)

## Ausgangspunkt
- Am 11.11. hat die Prüfung aller Tasks unter datahub zwei Probleme ergeben:
  - DH-051: Beim DSL-Speedtest fehlen Messungen, weil Ookla mit 429 ablehnt.
  - DH-056: `status.py` belegte nach 18 Tagen 7,3 GB. Am 11.11. gab es einen Notfall-Neustart.

## Bearbeitete Themen
- **DH-051 DSL:** Bei 429 wird die Messung ausgelassen, ohne Ersatzmessung. Intervall 1800 s, Telegram nach 3 h ohne Messung. Commits `69ff8e1` und `70bf492`, Neustart des Tasks `DSL Speedtest Monitoring` um 13:34.
- **DH-056 status.py:**
  - Ursache war `multitasking` (von yfinance), das jeden Thread dauerhaft festhält. Dazu kamen 152 Abrufe je Runde.
  - Lösung: `threads=False`, Zwischenspeicher für die Referenzkurse (nur exakte Treffer), Monatsvergleich einmal je Runde, keine Ausgabe je Runde.
  - Commits `e1cd736` und `4318e07`, Neustart des `Stock Monitoring Service` um 15:49.
- `CLAUDE.md`: zwei neue Einträge unter „Known Issues and Fixes“, Datenfluss aktualisiert.

## Entscheidungen & Erkenntnisse
- Ein Dauerläufer darf `yf.download` nur mit `threads=False` aufrufen.
- Referenzkurse ändern sich nur einmal am Tag. Ein Ersatzkurs darf aber nicht in den Zwischenspeicher, weil er sonst den ganzen Tag stehen bliebe.
- DSL: Lieber weniger Messungen gegen Telekom Stuttgart als gemischt mit Telefónica Berlin (Entscheidung AH).

## Verworfene Ansätze
- `multitasking.config["TASKS"]` je Runde leeren: greift in Interna einer fremden Bibliothek ein.
- Regelmäßiger Neustart per Task: behandelt nur das Symptom.
- DSL: Ersatzmessung bei 429 behalten, Intervall 20 Min.

## Nächster Schritt beim Wiederaufnehmen
- Am 13.11. den Verlauf messen: Handles und Speicher von `status.py` sollen über den ganzen Tag flach bleiben. `status_dsl.py` lag 2 h nach dem Start bei 296 MB, prüfen, ob das wächst. DSL: rund 2 Messungen je Stunde ohne 429?

## Noch offene Punkte
- Die Startskripte puffern stdout bis Prozessende, sie sollen zeilenweise ins Monatslog schreiben (datahub DH-063).
- Speicherwarnung im Watchdog (hauserver HS-22).
