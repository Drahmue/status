# Changelog - 2026-07-20

## Zusammenfassung

Zugriff auf das Web-Dashboard (`http://192.168.178.40:5000`) war vom Rechner "ahmain" aus nicht möglich. Ursache war keine fehlerhafte Konfiguration von `status.py` oder `app.py`, sondern eine fehlende Windows-Firewall-Regel für eingehende Verbindungen auf Port 5000.

## Symptom

Firefox auf ahmain konnte `192.168.178.40:5000` nicht erreichen (Timeout/keine Verbindung).

## Diagnose

Geprüft und als Ursache ausgeschlossen:
- **Stock Monitoring Service** (`status.py`): Task-Status `Running` ✓
- **Status Web App** (`app.py`): Task-Status `Running` ✓, Flask-Prozess lauscht lokal korrekt auf `0.0.0.0:5000` (`Get-NetTCPConnection -LocalPort 5000` zeigt `Listen`) ✓
- Server-IP korrekt: `192.168.178.40` (Ethernet-Adapter) ✓

Root Cause gefunden:
- `Get-NetFirewallRule -DisplayName "*5000*"` und Suche nach Port-Filtern auf TCP 5000 lieferten **keine Treffer** — es existierte keinerlei Inbound-Regel für Port 5000.
- Alle drei Firewall-Profile (Domain, Private, Public) waren aktiv (`Enabled = True`), sodass eingehende Verbindungen ohne explizite Allow-Regel standardmäßig blockiert werden.
- Der Flask-Dev-Server war somit nur vom Server selbst (`localhost`) erreichbar, nicht aus dem LAN.

## Fix

```powershell
New-NetFirewallRule -DisplayName "Flask Status Web App (Port 5000)" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Domain,Private
```

Bewusst **nicht** für das Profil `Public` freigegeben, um die Angriffsfläche auf vertrauenswürdige Netze (Heimnetz/Domain) zu beschränken.

## Sicherheitsbewertung

Vor dem Anlegen der Regel wurde geprüft, ob die Öffnung von Port 5000 ein Sicherheitsrisiko darstellt:

- **Profil-Beschränkung:** Regel gilt nur für `Domain` und `Private`, nicht `Public` — kein Zugriff aus nicht vertrauenswürdigen Netzen.
- **Kein Debug-Modus:** `app.py:11` startet Flask mit `app.run(host="0.0.0.0")` **ohne** `debug=True` — der Werkzeug-Debugger (RCE-Risiko) ist inaktiv.
- **Kein Internet-Exposure:** Kein Port-Forwarding auf dem Router nötig; externer Fernzugriff läuft bereits sauber getrennt über Tailscale VPN (siehe CHANGELOG_2026-05-21.md).
- **Bekannte Restrisiken:** Keine Authentifizierung auf dem Dashboard — jedes Gerät im Heimnetz kann ohne Login auf Portfolio-/Zählerdaten zugreifen. Für das vertrauenswürdige Heimnetz als akzeptabel bewertet.

**Ergebnis:** Vom Nutzer als akzeptabel eingestuft (informelles Review, keine Auth-Ergänzung angefordert).

## Verifikation

Zugriff von ahmain auf `http://192.168.178.40:5000` erfolgreich getestet.

## Geänderte/Neue Dateien

- **NEU:** `CHANGELOG_2026-07-20.md` (dieses Dokument)
- **GEÄNDERT:** `CHANGELOG.md` (Master) — Eintrag in Changelog-Übersicht ergänzt
- **System:** Neue Windows-Firewall-Regel `Flask Status Web App (Port 5000)` (Inbound, TCP 5000, Domain+Private, Allow)

## Referenzen

- **Verwandte Dokumente:** `CLAUDE.md`, `CHANGELOG_2026-05-21.md` (Tailscale-Setup)
