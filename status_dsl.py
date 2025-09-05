# -*- coding: utf-8 -*-
"""
Status DSL - DSL Speedtest monitoring script
Based on DSL Speedtest v2
Simplified version without Excel export functionality
Updates speedtest.json file for web interface
"""

import os
import sys
import re
import json
import subprocess
import traceback
import configparser
import time
from datetime import datetime

# Python-Speedtest (sivel/speedtest)
import speedtest
import pandas as pd


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


def set_working_directory(logfile=None, screen=True):
    """Set working directory to script location"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        screen_and_log(f"Arbeitsverzeichnis gesetzt auf: {script_dir}", logfile, screen)
        return script_dir
    except Exception as e:
        screen_and_log(f"Fehler beim Setzen des Arbeitsverzeichnisses: {e}", logfile, screen)
        return None


def normalize_path(path_value, base_dir):
    """Normalize and expand path relative to base directory"""
    if not path_value:
        return None
    path_value = os.path.expandvars(os.path.expanduser(path_value))
    if not os.path.isabs(path_value):
        path_value = os.path.abspath(os.path.join(base_dir, path_value))
    return os.path.normpath(path_value)


def settings_import(settings_file, logfile=None, screen=True):
    """Import settings from INI file with error tolerance and defaults"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Default settings
    defaults = {
        "logfile": "status_dsl.log",
        "json_output": os.path.join("static", "speedtest.json"),
        "parquet_data": "speedtest_data.parquet",
        "cli_path": "",
        "use_ookla_cli": True,
        "secure": True,
        "server_id": "31448",  # Telekom Frankfurt
        "sponsor": "Telekom",
        "city": "Frankfurt",
        "country": "Germany",
        "refresh_time": 300,  # 5 minutes default
    }

    cfg = configparser.ConfigParser()
    settings = {}

    if os.path.exists(settings_file):
        try:
            cfg.read(settings_file, encoding="utf-8")
            screen_and_log(f"Konfigurationsdatei geladen: {settings_file}", logfile, screen)
        except Exception as e:
            screen_and_log(f"WARN: INI konnte nicht gelesen werden ({e}). Nutze Defaults.", logfile, screen)
    else:
        screen_and_log(f"WARN: Konfigurationsdatei nicht gefunden: {settings_file}. Nutze Defaults.", logfile, screen)

    # Files section
    files = dict(cfg.items("Files")) if cfg.has_section("Files") else {}
    settings["logfile"] = normalize_path(files.get("logfile", defaults["logfile"]), base_dir)
    settings["json_output"] = normalize_path(files.get("json_output", defaults["json_output"]), base_dir)
    settings["parquet_data"] = normalize_path(files.get("parquet_data", defaults["parquet_data"]), base_dir)

    # Speedtest section
    speedtest_section = dict(cfg.items("Speedtest")) if cfg.has_section("Speedtest") else {}
    settings["speedtest"] = {
        "server_id": (speedtest_section.get("server_id", defaults["server_id"]) or "").strip(),
        "use_ookla_cli": (speedtest_section.get("use_ookla_cli", "true") or "true").strip().lower() in ("1", "true", "yes", "on"),
        "cli_path": normalize_path((speedtest_section.get("cli_path", defaults["cli_path"]) or "").strip(), base_dir),
        "secure": (speedtest_section.get("secure", "true") or "true").strip().lower() in ("1", "true", "yes", "on"),
        "sponsor": (speedtest_section.get("sponsor", defaults["sponsor"]) or "").strip(),
        "city": (speedtest_section.get("city", defaults["city"]) or "").strip(),
        "country": (speedtest_section.get("country", defaults["country"]) or "").strip(),
    }

    # Timing section
    timing_section = dict(cfg.items("Timing")) if cfg.has_section("Timing") else {}
    try:
        settings["refresh_time"] = int(timing_section.get("refresh_time", defaults["refresh_time"]))
    except (ValueError, TypeError):
        settings["refresh_time"] = defaults["refresh_time"]

    # Create directories if needed
    for key in ("logfile", "json_output", "parquet_data"):
        path_value = settings.get(key)
        if path_value:
            directory = os.path.dirname(path_value)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    screen_and_log(f"Ordner erstellt: {directory}", logfile, screen)
                except Exception as e:
                    screen_and_log(f"ERROR: Konnte Ordner nicht erstellen ({directory}): {e}", logfile, screen)

    return settings


def bytes_per_sec_to_mbps(bps_bytes):
    """Convert bytes per second to Mbps"""
    try:
        return round((float(bps_bytes) / 125000.0), 2)  # Bytes/s -> Mbit/s
    except Exception:
        return None


def perform_speedtest_cli(cli_path, logfile, screen=True, server_id=None, secure=True, timeout=180):
    """Perform speedtest using Ookla CLI"""
    try:
        # Log version (best effort)
        try:
            version_process = subprocess.run([cli_path, "--version"], capture_output=True, text=True, timeout=10)
            if version_process.returncode == 0:
                screen_and_log(f"Ookla-CLI Version: {version_process.stdout.strip()}", logfile, screen)
        except Exception:
            pass

        base_cmd = [cli_path, "--accept-license", "--accept-gdpr", "--format=json"]
        if server_id:
            base_cmd += ["--server-id", str(server_id)]

        # Try with --secure first, then without
        cmd_variants = []
        if secure:
            cmd_variants.append(base_cmd + ["--secure"])
        cmd_variants.append(base_cmd[:])

        for cmd in cmd_variants:
            screen_and_log(f"Starte Ookla-CLI: {' '.join(cmd)}", logfile, screen)
            completed_process = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            if completed_process.returncode == 0:
                try:
                    data = json.loads(completed_process.stdout)
                except Exception as e:
                    screen_and_log(f"ERROR: Ungültiges JSON der Ookla-CLI: {e}", logfile, screen)
                    continue

                server = data.get("server", {}) or {}
                ping = (data.get("ping", {}) or {}).get("latency")
                dl_bps = (data.get("download", {}) or {}).get("bandwidth")
                ul_bps = (data.get("upload", {}) or {}).get("bandwidth")
                ext_ip = (data.get("interface", {}) or {}).get("externalIp")

                result = {
                    "server_name": server.get("name") or server.get("host") or server.get("sponsor") or "Unknown",
                    "server_location": f"{server.get('location','Unknown')}, {server.get('country','Unknown')}",
                    "download_mbps": bytes_per_sec_to_mbps(dl_bps),
                    "upload_mbps": bytes_per_sec_to_mbps(ul_bps),
                    "ping_ms": round(float(ping), 2) if ping is not None else None,
                    "ip_address": ext_ip or "Unknown",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                server_id_found = server.get("id")
                if server_id_found:
                    screen_and_log(f"CLI-Server: {result['server_name']} – {result['server_location']} (ID {server_id_found})",
                                   logfile, screen)
                return result

            err = (completed_process.stderr or "").strip()
            screen_and_log(f"WARN: Ookla-CLI fehlgeschlagen (rc={completed_process.returncode}, stderr={err})", logfile, screen)

        screen_and_log("ERROR: Ookla-CLI Messung fehlgeschlagen (alle Varianten).", logfile, screen)
        return None

    except subprocess.TimeoutExpired:
        screen_and_log("ERROR: Ookla-CLI Timeout.", logfile, screen)
        return None
    except Exception as e:
        screen_and_log(f"ERROR: Unerwarteter Fehler in perform_speedtest_cli: {e}", logfile, screen)
        tb = traceback.format_exc()
        screen_and_log(tb, logfile, screen)
        return None


def perform_speedtest_py(logfile, screen=True, server_id=None, sponsor=None, city=None, country=None, secure=True):
    """Perform speedtest using Python speedtest library"""
    def log_exception(prefix, exception):
        screen_and_log(f"{prefix}: {exception.__class__.__name__}: {exception}", logfile, screen)
        tb = traceback.format_exc()
        screen_and_log(tb, logfile, screen)

    sponsor_filter = (sponsor or "").strip() or "Telekom"
    city_filter = (city or "").strip() or "Frankfurt"
    country_filter = (country or "").strip()

    screen_and_log("DSL-Speedtest beginnt...", logfile, screen)
    try:
        st = speedtest.Speedtest(secure=bool(secure))
        try:
            st.get_config()
        except Exception as e:
            log_exception("ERROR: Konnte Speedtest-Konfiguration nicht laden", e)
            return None

        best_server = None

        # Try fixed server ID first
        if server_id:
            try:
                st.get_servers([int(server_id)])
                best_server = st.get_best_server()
                screen_and_log(
                    f"Fester Server (per ID) gewählt: {best_server['sponsor']} – "
                    f"{best_server['name']}, {best_server['country']} (ID {server_id})",
                    logfile, screen
                )
            except Exception as e:
                log_exception("WARN: Fester Server per ID nicht verfügbar", e)
                best_server = None

        # Filter by sponsor/city/country
        if not best_server:
            try:
                st = speedtest.Speedtest(secure=bool(secure))
                st.get_config()
                st.get_servers()
                candidates = []
                for srv_list in st.servers.values():
                    for srv in srv_list:
                        sponsor_lc = (srv.get("sponsor", "") or "").lower()
                        city_lc = (srv.get("name", "") or "").lower()
                        country_lc = (srv.get("country", "") or "").lower()
                        sponsor_ok = bool(re.search(r'\b(deutsche\s+)?telekom\b', sponsor_lc))
                        if sponsor_filter:
                            sponsor_ok = sponsor_ok and (sponsor_filter.lower() in sponsor_lc or sponsor_filter.lower() == "telekom")
                        city_ok = (city_filter.lower() in city_lc) if city_filter else True
                        country_ok = (country_filter.lower() in country_lc) if country_filter else True
                        if sponsor_ok and city_ok and country_ok:
                            candidates.append(srv)
                if candidates:
                    ids = [int(s["id"]) for s in candidates if "id" in s]
                    st.get_servers(ids)
                    best_server = st.get_best_server()
                    screen_and_log(
                        f"Telekom/Frankfurt-Server gewählt: {best_server['sponsor']} – "
                        f"{best_server['name']}, {best_server['country']} (ID {best_server.get('id')})",
                        logfile, screen
                    )
                else:
                    screen_and_log("WARN: Kein Telekom-Server in Frankfurt gefunden – Fallback auf best_server()", logfile, screen)
            except Exception as e:
                log_exception("WARN: Sponsor/City-Filter fehlgeschlagen", e)

        # Fallback to best server
        if not best_server:
            try:
                st = speedtest.Speedtest(secure=bool(secure))
                st.get_config()
                st.get_servers()
                best_server = st.get_best_server()
                screen_and_log(
                    f"Fallback-Server: {best_server['sponsor']} – "
                    f"{best_server['name']}, {best_server['country']} (ID {best_server.get('id')})",
                    logfile, screen
                )
            except Exception as e:
                log_exception("ERROR: Fallback get_best_server() fehlgeschlagen", e)
                return None

        # Perform measurement
        try:
            download_speed = st.download() / 1_000_000
            upload_speed = st.upload() / 1_000_000
            ping_value = st.results.ping
        except Exception as e:
            log_exception("ERROR: Download/Upload/Ping fehlgeschlagen", e)
            return None

        return {
            "server_name": best_server['sponsor'],
            "server_location": f"{best_server['name']}, {best_server['country']}",
            "download_mbps": round(download_speed, 2),
            "upload_mbps": round(upload_speed, 2),
            "ping_ms": round(ping_value, 2),
            "ip_address": st.results.client['ip'],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        log_exception("ERROR: Unerwarteter Fehler beim DSL-Speedtest", e)
        return None


def save_results_to_json(results, json_target, logfile, screen=True):
    """Save speedtest results to JSON file"""
    try:
        os.makedirs(os.path.dirname(json_target), exist_ok=True)
        
        with open(json_target, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        screen_and_log(f"JSON geschrieben: '{json_target}'", logfile, screen)
        return json_target

    except Exception as e:
        screen_and_log(f"ERROR: JSON-Schreiben fehlgeschlagen: {e}", logfile, screen)
        return None


def save_results_to_parquet(results, parquet_file, logfile, screen=True):
    """Save speedtest results to Parquet file for efficient data storage"""
    try:
        # Convert results to DataFrame
        df_new = pd.DataFrame([{
            'timestamp': pd.to_datetime(results['timestamp']),
            'server_name': results['server_name'],
            'server_location': results['server_location'],
            'download_mbps': results['download_mbps'],
            'upload_mbps': results['upload_mbps'],
            'ping_ms': results['ping_ms'],
            'ip_address': results['ip_address']
        }])
        
        # Check if parquet file exists
        if os.path.exists(parquet_file):
            # Load existing data and append
            try:
                df_existing = pd.read_parquet(parquet_file)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Sort by timestamp and remove duplicates
                df_combined = df_combined.sort_values('timestamp').drop_duplicates(
                    subset=['timestamp'], keep='last'
                )
                
                df_combined.to_parquet(parquet_file, index=False)
                screen_and_log(f"Parquet-Daten aktualisiert: '{parquet_file}' ({len(df_combined)} Einträge)", logfile, screen)
                
            except Exception as e:
                screen_and_log(f"WARN: Bestehende Parquet-Datei konnte nicht gelesen werden ({e}). Erstelle neue Datei.", logfile, screen)
                df_new.to_parquet(parquet_file, index=False)
                screen_and_log(f"Neue Parquet-Datei erstellt: '{parquet_file}'", logfile, screen)
        else:
            # Create new parquet file
            df_new.to_parquet(parquet_file, index=False)
            screen_and_log(f"Neue Parquet-Datei erstellt: '{parquet_file}'", logfile, screen)
        
        return parquet_file

    except Exception as e:
        screen_and_log(f"ERROR: Parquet-Schreiben fehlgeschlagen: {e}", logfile, screen)
        tb = traceback.format_exc()
        screen_and_log(tb, logfile, screen)
        return None


def run_single_speedtest(settings, logfile):
    """Run a single speedtest and save results"""
    speed_cfg = settings.get("speedtest", {})
    json_file = settings["json_output"]
    parquet_file = settings["parquet_data"]
    
    server_id = speed_cfg.get("server_id") or None
    use_cli = bool(speed_cfg.get("use_ookla_cli"))
    cli_path = speed_cfg.get("cli_path")
    secure = bool(speed_cfg.get("secure", True))
    sponsor = speed_cfg.get("sponsor") or ""
    city = speed_cfg.get("city") or ""
    country = speed_cfg.get("country") or ""

    results = None
    
    # Try Ookla CLI first if configured
    if use_cli and cli_path and os.path.exists(cli_path):
        results = perform_speedtest_cli(cli_path, logfile, server_id=server_id, secure=secure)
        if not results:
            screen_and_log("WARN: CLI-Messung fehlgeschlagen – Fallback auf Python-Lib.", logfile, True)

    # Fallback to Python library
    if not results:
        if use_cli and (not cli_path or not os.path.exists(cli_path)):
            screen_and_log("WARN: CLI angefordert, aber cli_path fehlt/ungültig – nutze Python-Lib.", logfile, True)
        results = perform_speedtest_py(
            logfile,
            server_id=server_id,
            sponsor=sponsor,
            city=city,
            country=country,
            secure=secure
        )

    if not results:
        screen_and_log("ERROR: DSL-Speedtest fehlgeschlagen.", logfile)
        return False

    # Save results to both JSON and Parquet
    json_written = save_results_to_json(results, json_file, logfile)
    parquet_written = save_results_to_parquet(results, parquet_file, logfile)
    
    if json_written and parquet_written:
        screen_and_log(f"Speedtest erfolgreich: Download {results.get('download_mbps')}Mbps, Upload {results.get('upload_mbps')}Mbps, Ping {results.get('ping_ms')}ms", logfile)
        return True
    elif json_written:
        screen_and_log("WARN: JSON erfolgreich, aber Parquet-Speicherung fehlgeschlagen.", logfile)
        return True  # Still successful if JSON works
    else:
        screen_and_log("ERROR: Beide Ausgaben fehlgeschlagen.", logfile)
        return False


def main():
    """Main function - runs continuous speedtest monitoring"""
    try:
        script_dir = set_working_directory()
        if not script_dir:
            sys.exit(1)
            
        settings_file = "status_dsl.ini"
        settings = settings_import(settings_file, logfile=None, screen=True)
        
        logfile = settings["logfile"]
        refresh_time = settings.get("refresh_time", 300)
        
        screen_and_log("Status DSL Speedtest monitoring gestartet", logfile, True)
        screen_and_log(f"Aktualisierungsintervall: {refresh_time} Sekunden", logfile, True)
        
        while True:
            try:
                success = run_single_speedtest(settings, logfile)
                if not success:
                    screen_and_log("WARN: Speedtest fehlgeschlagen, versuche es beim nächsten Zyklus erneut.", logfile)
                
                screen_and_log(f"Warte {refresh_time} Sekunden bis zum nächsten Test...", logfile, True)
                time.sleep(refresh_time)
                
            except KeyboardInterrupt:
                screen_and_log("Programm durch Benutzer beendet (Ctrl+C)", logfile, True)
                break
            except Exception as e:
                screen_and_log(f"ERROR: Unerwarteter Fehler im Hauptloop: {e}", logfile, True)
                tb = traceback.format_exc()
                screen_and_log(tb, logfile, True)
                time.sleep(refresh_time)

    except Exception as e:
        screen_and_log(f"ERROR: Kritischer Fehler: {e}", None, True)
        tb = traceback.format_exc()
        screen_and_log(tb, None, True)
        sys.exit(99)


if __name__ == "__main__":
    main()