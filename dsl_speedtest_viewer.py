# -*- coding: utf-8 -*-
"""
DSL Speedtest Viewer - Viewer für gespeicherte DSL Speedtest Daten
Liest Parquet-Dateien und zeigt Statistiken und Verlauf an
"""

import os
import sys
import configparser
import pandas as pd
from datetime import datetime, timedelta
import traceback


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
    """Import settings from INI file"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    defaults = {
        "logfile": "dsl_speedtest_viewer.log",
        "parquet_data": "speedtest_data.parquet",
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
        # Try to read from status_dsl.ini if viewer config doesn't exist
        status_dsl_ini = "status_dsl.ini"
        if os.path.exists(status_dsl_ini):
            try:
                cfg.read(status_dsl_ini, encoding="utf-8")
                screen_and_log(f"Konfiguration von status_dsl.ini übernommen", logfile, screen)
            except Exception as e:
                screen_and_log(f"WARN: status_dsl.ini konnte nicht gelesen werden ({e}). Nutze Defaults.", logfile, screen)
        else:
            screen_and_log(f"WARN: Keine Konfigurationsdatei gefunden. Nutze Defaults.", logfile, screen)

    # Files section
    files = dict(cfg.items("Files")) if cfg.has_section("Files") else {}
    settings["logfile"] = normalize_path(files.get("logfile", defaults["logfile"]), base_dir)
    settings["parquet_data"] = normalize_path(files.get("parquet_data", defaults["parquet_data"]), base_dir)

    return settings


def load_speedtest_data(parquet_file, logfile=None, screen=True):
    """Load speedtest data from Parquet file"""
    try:
        if not os.path.exists(parquet_file):
            screen_and_log(f"ERROR: Parquet-Datei nicht gefunden: {parquet_file}", logfile, screen)
            return None
        
        df = pd.read_parquet(parquet_file)
        screen_and_log(f"Speedtest-Daten geladen: {len(df)} Einträge aus '{parquet_file}'", logfile, screen)
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        
        return df
    
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Laden der Parquet-Datei: {e}", logfile, screen)
        tb = traceback.format_exc()
        screen_and_log(tb, logfile, screen)
        return None


def display_summary_statistics(df, logfile=None, screen=True):
    """Display summary statistics for speedtest data"""
    if df is None or df.empty:
        screen_and_log("Keine Daten zum Anzeigen verfügbar.", logfile, screen)
        return
    
    print("\n" + "="*60)
    print("DSL SPEEDTEST STATISTIKEN")
    print("="*60)
    
    # Basic info
    total_tests = len(df)
    date_range = f"{df['timestamp'].min().strftime('%Y-%m-%d')} bis {df['timestamp'].max().strftime('%Y-%m-%d')}"
    
    print(f"Anzahl Tests: {total_tests}")
    print(f"Zeitraum: {date_range}")
    
    # Speed statistics
    print(f"\nDOWNLOAD GESCHWINDIGKEIT (Mbps):")
    print(f"  Durchschnitt: {df['download_mbps'].mean():.2f}")
    print(f"  Minimum:      {df['download_mbps'].min():.2f}")
    print(f"  Maximum:      {df['download_mbps'].max():.2f}")
    print(f"  Median:       {df['download_mbps'].median():.2f}")
    
    print(f"\nUPLOAD GESCHWINDIGKEIT (Mbps):")
    print(f"  Durchschnitt: {df['upload_mbps'].mean():.2f}")
    print(f"  Minimum:      {df['upload_mbps'].min():.2f}")
    print(f"  Maximum:      {df['upload_mbps'].max():.2f}")
    print(f"  Median:       {df['upload_mbps'].median():.2f}")
    
    print(f"\nPING (ms):")
    print(f"  Durchschnitt: {df['ping_ms'].mean():.2f}")
    print(f"  Minimum:      {df['ping_ms'].min():.2f}")
    print(f"  Maximum:      {df['ping_ms'].max():.2f}")
    print(f"  Median:       {df['ping_ms'].median():.2f}")
    
    # Server statistics
    server_counts = df['server_name'].value_counts()
    print(f"\nVERWENDETE SERVER:")
    for server, count in server_counts.items():
        percentage = (count / total_tests) * 100
        print(f"  {server}: {count} Tests ({percentage:.1f}%)")


def display_recent_tests(df, days=7, logfile=None, screen=True):
    """Display recent speedtest results"""
    if df is None or df.empty:
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_df = df[df['timestamp'] >= cutoff_date].copy()
    
    if recent_df.empty:
        print(f"\nKeine Tests in den letzten {days} Tagen gefunden.")
        return
    
    print(f"\n" + "="*80)
    print(f"LETZTE {len(recent_df)} SPEEDTESTS (Letzten {days} Tage)")
    print("="*80)
    
    # Sort by timestamp descending (newest first)
    recent_df = recent_df.sort_values('timestamp', ascending=False)
    
    print(f"{'Zeitpunkt':<20} {'Download':<10} {'Upload':<8} {'Ping':<8} {'Server':<25}")
    print("-" * 80)
    
    for _, row in recent_df.head(20).iterrows():  # Show max 20 recent tests
        timestamp = row['timestamp'].strftime('%Y-%m-%d %H:%M')
        download = f"{row['download_mbps']:.1f} Mbps"
        upload = f"{row['upload_mbps']:.1f} Mbps"
        ping = f"{row['ping_ms']:.1f} ms"
        server = row['server_name'][:24]  # Truncate long server names
        
        print(f"{timestamp:<20} {download:<10} {upload:<8} {ping:<8} {server:<25}")


def display_daily_averages(df, days=30, logfile=None, screen=True):
    """Display daily averages for the specified number of days"""
    if df is None or df.empty:
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_df = df[df['timestamp'] >= cutoff_date].copy()
    
    if recent_df.empty:
        print(f"\nKeine Tests in den letzten {days} Tagen für Durchschnittswerte gefunden.")
        return
    
    # Group by date
    recent_df['date'] = recent_df['timestamp'].dt.date
    daily_avg = recent_df.groupby('date').agg({
        'download_mbps': 'mean',
        'upload_mbps': 'mean',
        'ping_ms': 'mean'
    }).round(2)
    
    print(f"\n" + "="*60)
    print(f"TÄGLICHE DURCHSCHNITTSWERTE (Letzten {days} Tage)")
    print("="*60)
    
    print(f"{'Datum':<12} {'Download':<12} {'Upload':<10} {'Ping':<8}")
    print("-" * 50)
    
    for date, row in daily_avg.sort_index(ascending=False).head(15).iterrows():  # Show max 15 days
        download = f"{row['download_mbps']:.1f} Mbps"
        upload = f"{row['upload_mbps']:.1f} Mbps" 
        ping = f"{row['ping_ms']:.1f} ms"
        
        print(f"{date!s:<12} {download:<12} {upload:<10} {ping:<8}")


def interactive_menu(df, settings, logfile):
    """Interactive menu for data viewing options"""
    while True:
        print("\n" + "="*60)
        print("DSL SPEEDTEST VIEWER - HAUPTMENÜ")
        print("="*60)
        print("1. Zusammenfassung & Statistiken")
        print("2. Letzte Tests anzeigen (7 Tage)")
        print("3. Tägliche Durchschnittswerte (30 Tage)")
        print("4. Daten neu laden")
        print("5. Beenden")
        print("-" * 60)
        
        try:
            choice = input("Wählen Sie eine Option (1-5): ").strip()
            
            if choice == "1":
                display_summary_statistics(df, logfile)
            elif choice == "2":
                display_recent_tests(df, days=7, logfile=logfile)
            elif choice == "3":
                display_daily_averages(df, days=30, logfile=logfile)
            elif choice == "4":
                print("Lade Daten neu...")
                df = load_speedtest_data(settings["parquet_data"], logfile)
                if df is not None:
                    print(f"✓ Daten neu geladen: {len(df)} Einträge")
                else:
                    print("✗ Fehler beim Laden der Daten")
            elif choice == "5":
                print("Programm wird beendet...")
                break
            else:
                print("Ungültige Auswahl. Bitte wählen Sie 1-5.")
                
        except KeyboardInterrupt:
            print("\nProgramm durch Benutzer beendet (Ctrl+C)")
            break
        except Exception as e:
            print(f"Fehler: {e}")
            

def main():
    """Main function - DSL Speedtest Viewer"""
    try:
        script_dir = set_working_directory()
        if not script_dir:
            sys.exit(1)
            
        settings_file = "dsl_speedtest_viewer.ini"
        settings = settings_import(settings_file, logfile=None, screen=True)
        
        logfile = settings["logfile"]
        
        screen_and_log("DSL Speedtest Viewer gestartet", logfile, True)
        
        # Load speedtest data
        df = load_speedtest_data(settings["parquet_data"], logfile)
        
        if df is None:
            screen_and_log("FEHLER: Keine Speedtest-Daten verfügbar. Programm wird beendet.", logfile, True)
            sys.exit(1)
        
        # Start interactive menu
        interactive_menu(df, settings, logfile)
        
        screen_and_log("DSL Speedtest Viewer beendet", logfile, True)

    except Exception as e:
        screen_and_log(f"ERROR: Kritischer Fehler: {e}", None, True)
        tb = traceback.format_exc()
        screen_and_log(tb, None, True)
        sys.exit(99)


if __name__ == "__main__":
    main()