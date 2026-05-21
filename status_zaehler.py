# -*- coding: utf-8 -*-
"""
Status Zaehler - Tasmota meter monitoring script
Fetches gas and electricity meter readings from local Tasmota devices
and exports them to static/zaehler.json for the web interface.
"""

import os
import sys
import re
import json
import traceback
import configparser
import time
import urllib.request
import urllib.error
from datetime import datetime


def screen_and_log(text, logfile=None, screen=True):
    """Log message to screen and/or file with timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {text}"
    if screen:
        print(line)
    if logfile:
        try:
            logdir = os.path.dirname(logfile)
            if logdir and not os.path.exists(logdir):
                os.makedirs(logdir, exist_ok=True)
            with open(logfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception as e:
            print(f"Fehler beim Schreiben ins Logfile: {e}")


def set_working_directory(logfile=None):
    """Set working directory to script location"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        screen_and_log(f"Arbeitsverzeichnis gesetzt auf: {script_dir}", logfile)
        return script_dir
    except Exception as e:
        screen_and_log(f"Fehler beim Setzen des Arbeitsverzeichnisses: {e}", logfile)
        return None


def normalize_path(path_value, base_dir):
    """Normalize and expand path relative to base directory"""
    if not path_value:
        return None
    path_value = os.path.expandvars(os.path.expanduser(path_value))
    if not os.path.isabs(path_value):
        path_value = os.path.abspath(os.path.join(base_dir, path_value))
    return os.path.normpath(path_value)


def settings_import(settings_file, logfile=None):
    """Import settings from INI file with error tolerance and defaults"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    defaults = {
        "logfile": "status_zaehler.log",
        "json_output": os.path.join("static", "zaehler.json"),
        "gas_url": "http://192.168.178.130/?m=1",
        "strom_url": "http://192.168.178.133/?m=1",
        "refresh_time": 300,
        "request_timeout": 10,
    }

    cfg = configparser.ConfigParser()
    settings = {}

    if os.path.exists(settings_file):
        try:
            cfg.read(settings_file, encoding="utf-8")
            screen_and_log(f"Konfigurationsdatei geladen: {settings_file}", logfile)
        except Exception as e:
            screen_and_log(f"WARN: INI konnte nicht gelesen werden ({e}). Nutze Defaults.", logfile)
    else:
        screen_and_log(f"WARN: Konfigurationsdatei nicht gefunden: {settings_file}. Nutze Defaults.", logfile)

    files = dict(cfg.items("Files")) if cfg.has_section("Files") else {}
    settings["logfile"] = normalize_path(files.get("logfile", defaults["logfile"]), base_dir)
    settings["json_output"] = normalize_path(files.get("json_output", defaults["json_output"]), base_dir)

    geraete = dict(cfg.items("Geraete")) if cfg.has_section("Geraete") else {}
    settings["gas_url"] = geraete.get("gas_url", defaults["gas_url"]).strip()
    settings["strom_url"] = geraete.get("strom_url", defaults["strom_url"]).strip()

    timing = dict(cfg.items("Timing")) if cfg.has_section("Timing") else {}
    try:
        settings["refresh_time"] = int(timing.get("refresh_time", defaults["refresh_time"]))
    except (ValueError, TypeError):
        settings["refresh_time"] = defaults["refresh_time"]
    try:
        settings["request_timeout"] = int(timing.get("request_timeout", defaults["request_timeout"]))
    except (ValueError, TypeError):
        settings["request_timeout"] = defaults["request_timeout"]

    # Create output directory if needed
    json_dir = os.path.dirname(settings["json_output"])
    if json_dir and not os.path.exists(json_dir):
        try:
            os.makedirs(json_dir, exist_ok=True)
        except Exception as e:
            screen_and_log(f"ERROR: Konnte Ausgabeverzeichnis nicht erstellen: {e}", logfile)

    return settings


def fetch_tasmota(url, timeout=10, logfile=None):
    """Fetch raw sensor data from a Tasmota device (?m=1 endpoint)"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        screen_and_log(f"ERROR: Verbindung zu {url} fehlgeschlagen: {e}", logfile)
        return None
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Abrufen von {url}: {e}", logfile)
        return None


def parse_gas(raw, logfile=None):
    """Parse gas meter data from Tasmota ?m=1 response"""
    if not raw:
        return None

    result = {}

    m = re.search(r'Zählerstand:\s*\{m\}\s*([\d.]+)\s*m³', raw)
    if m:
        result["zaehlerstand_m3"] = float(m.group(1))
    else:
        screen_and_log("WARN: Gaszählerstand nicht gefunden", logfile)
        result["zaehlerstand_m3"] = None

    return result


def parse_strom(raw, logfile=None):
    """Parse electricity meter data from Tasmota ?m=1 response"""
    if not raw:
        return None

    result = {}

    m = re.search(r'MT691 Total Consumed\{m\}([\d.]+)\s*kWh', raw)
    result["bezug_kwh"] = float(m.group(1)) if m else None
    if not m:
        screen_and_log("WARN: MT691 Total Consumed nicht gefunden", logfile)

    m = re.search(r'MT691 Total Delivered\{m\}([\d.]+)\s*kWh', raw)
    result["einspeisung_kwh"] = float(m.group(1)) if m else None
    if not m:
        screen_and_log("WARN: MT691 Total Delivered nicht gefunden", logfile)

    # Gesamtverbrauch (ohne P1/P2/P3 - erste Zeile ohne Phasenangabe)
    m = re.search(r'MT691 Current Consumption\{m\}(\d+)\s*W', raw)
    result["aktuell_w"] = int(m.group(1)) if m else None
    if not m:
        screen_and_log("WARN: MT691 Current Consumption nicht gefunden", logfile)

    return result


def fetch_and_parse(settings, logfile):
    """Fetch data from both Tasmota devices and return combined result"""
    timeout = settings["request_timeout"]

    screen_and_log(f"Rufe Gaszähler ab: {settings['gas_url']}", logfile)
    gas_raw = fetch_tasmota(settings["gas_url"], timeout=timeout, logfile=logfile)
    gas_data = parse_gas(gas_raw, logfile)

    screen_and_log(f"Rufe Stromzähler ab: {settings['strom_url']}", logfile)
    strom_raw = fetch_tasmota(settings["strom_url"], timeout=timeout, logfile=logfile)
    strom_data = parse_strom(strom_raw, logfile)

    if gas_data is None and strom_data is None:
        screen_and_log("ERROR: Beide Geräte nicht erreichbar", logfile)
        return None

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gas": gas_data or {"zaehlerstand_m3": None},
        "strom": strom_data or {"bezug_kwh": None, "einspeisung_kwh": None, "aktuell_w": None},
    }


def save_json(data, json_path, logfile):
    """Write result data to JSON file"""
    try:
        json_dir = os.path.dirname(json_path)
        if json_dir:
            os.makedirs(json_dir, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        screen_and_log(f"JSON geschrieben: '{json_path}'", logfile)
        return True
    except Exception as e:
        screen_and_log(f"ERROR: JSON-Schreiben fehlgeschlagen: {e}", logfile)
        return False


def main():
    """Main function - runs continuous meter monitoring"""
    try:
        script_dir = set_working_directory()
        if not script_dir:
            sys.exit(1)

        settings_file = "status_zaehler.ini"
        settings = settings_import(settings_file, logfile=None)

        logfile = settings["logfile"]
        refresh_time = settings["refresh_time"]

        screen_and_log("Status Zaehler Monitoring gestartet", logfile)
        screen_and_log(f"Aktualisierungsintervall: {refresh_time} Sekunden", logfile)

        while True:
            try:
                data = fetch_and_parse(settings, logfile)
                if data:
                    save_json(data, settings["json_output"], logfile)
                    screen_and_log(
                        f"Gas: {data['gas'].get('zaehlerstand_m3')} m³ | "
                        f"Strom Bezug: {data['strom'].get('bezug_kwh')} kWh | "
                        f"Einspeisung: {data['strom'].get('einspeisung_kwh')} kWh | "
                        f"Aktuell: {data['strom'].get('aktuell_w')} W",
                        logfile
                    )
                else:
                    screen_and_log("WARN: Keine Daten – überspringe JSON-Update", logfile)

                screen_and_log(f"Warte {refresh_time} Sekunden...", logfile)
                time.sleep(refresh_time)

            except KeyboardInterrupt:
                screen_and_log("Programm durch Benutzer beendet (Ctrl+C)", logfile)
                break
            except Exception as e:
                screen_and_log(f"ERROR: Unerwarteter Fehler im Hauptloop: {e}", logfile)
                screen_and_log(traceback.format_exc(), logfile)
                time.sleep(refresh_time)

    except Exception as e:
        screen_and_log(f"ERROR: Kritischer Fehler: {e}", None)
        screen_and_log(traceback.format_exc(), None)
        sys.exit(99)


if __name__ == "__main__":
    main()
