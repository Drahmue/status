import pandas as pd
import yfinance as yf
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import importlib
from holidays.countries.germany import Germany
import time
import json

# ALLGEMEINE FUNKTIONEN

# Standardbiblithek einbinden
standard_library_path = r"\\WIN-H7BKO5H0RMC\Dataserver\Programmier Projekte\Python\Standardbibliothek"
library_name = "Standardfunktionen_aktuell.py"

# Sicherstellen, dass der Pfad existiert
if not os.path.exists(standard_library_path):
    sys.exit(f"Fehler: Der Pfad '{standard_library_path}' existiert nicht. Bitte überprüfe die Eingabe.")

# Sicherstellen, dass die Bibliothek existiert
library_full_path = os.path.join(standard_library_path, library_name)
if not os.path.isfile(library_full_path):
    sys.exit(f"Fehler: Die Bibliothek '{library_name}' wurde im Pfad '{standard_library_path}' nicht gefunden.")

# Pfad zum Suchpfad hinzufügen
sys.path.insert(0, standard_library_path)

# Bibliothek importieren
try:
    import Standardfunktionen_aktuell
    importlib.reload(Standardfunktionen_aktuell)
    from Standardfunktionen_aktuell import (
        screen_and_log,
        set_working_directory,
        settings_import,
        files_availability_check
    )
    print(f"Import der Bibliothek: {library_name} von {standard_library_path} erfolgreich")
except ImportError as e:
    sys.exit(f"Fehler beim Import der Bibliothek: {e}")


def function_result(function_name, error_count, warning_count, logfile, screen=True):
    """
    Überprüft die Rückgabewerte einer Funktion und gibt eine entsprechende Meldung aus.
    Beendet das Programm, wenn Fehler aufgetreten sind.
    """
    if error_count > 0:
        screen_and_log(f"ERROR: {function_name} fehlgeschlagen. Das Programm wird beendet.", logfile, screen=True)
        sys.exit(1)
    elif warning_count > 0:
        screen_and_log(f"WARNING: {function_name} abgeschlossen mit {warning_count} Warnung(en).", logfile, screen=True)
    else:
        screen_and_log(f"Info: {function_name} erfolgreich abgeschlossen.", logfile, screen=True)


# Spezifische Funktionen
def instruments_import(filename, logfile, screen=True):
    """
    Liest die Excel-Datei und importiert die ersten vier Spalten (wkn, ticker, instrument_name, Default)
    """
    try:
        if not filename.endswith(('.xlsx', '.xls')):
            raise ValueError(f"Die Datei '{filename}' ist keine Excel-Datei.")

        df = pd.read_excel(filename, usecols=[0, 1, 2, 3], index_col=0)
        df.index = df.index.str.lower()  
        df['ticker'] = df['ticker'].str.lower()  
        df.columns = ['ticker', 'instrument_name', 'default_value'] 
        return df

    except FileNotFoundError:
        screen_and_log(f"ERROR: Die Datei '{filename}' wurde nicht gefunden.", logfile, screen=screen)
        return None
    except ValueError as ve:
        screen_and_log(f"ERROR: {ve}", logfile, screen=screen)
        return None
    except Exception as e:
        screen_and_log(f"ERROR: Ein Fehler ist aufgetreten: {e}", logfile, screen=screen)
        return None


def bookings_import(filename, logfile, screen=True):
    """Liest Buchungsdaten aus Excel-Datei"""
    try:
        df = pd.read_excel(filename, usecols=[0, 1, 2, 3], names=['date', 'wkn', 'bank', 'delta'])
        df['wkn'] = df['wkn'].str.lower()
        df['bank'] = df['bank'].str.lower()
        df.dropna(subset=['wkn', 'bank', 'delta'], inplace=True)
        df.set_index(['date', 'wkn', 'bank'], inplace=True)
        df = df.groupby(level=['date', 'wkn', 'bank']).sum()
        return df
    except FileNotFoundError:
        screen_and_log(f"Fehler: Die Datei '{filename}' wurde nicht gefunden.", logfile, screen=screen)
        return None
    except Exception as e:
        screen_and_log(f"Ein Fehler ist beim Import der Buchungen aus '{filename}' aufgetreten: {e}", logfile, screen=screen)
        return None


def bookings_check_for_instruments(bookings, instruments):
    """Überprüft, ob alle wkns aus 'bookings' im DataFrame 'instruments' vorhanden sind"""
    wkn_bookings = set(bookings.index.get_level_values('wkn'))
    wkn_instruments = set(instruments.index)
    missing_in_instruments = list(wkn_bookings - wkn_instruments)
    return missing_in_instruments


def shares_from_bookings(bookings, end_date, logfile, screen=False):
    """Erweitert den DataFrame `bookings` mit allen Kombinationen von Datum, wkn und Bank bis zu einem angegebenen Enddatum und berechnet die laufende Summe."""
    all_dates = pd.date_range(bookings.index.get_level_values('date').min(), end_date)
    wkns = bookings.index.get_level_values('wkn').unique()
    banks = bookings.index.get_level_values('bank').unique()
    
    full_index = pd.MultiIndex.from_product([all_dates, wkns, banks], names=['date', 'wkn', 'bank'])
    bookings_expanded = bookings.reindex(full_index).fillna(0)
    bookings_expanded['delta'] = bookings_expanded.groupby(['wkn', 'bank'])['delta'].cumsum()
    bookings_expanded['delta'] = bookings_expanded['delta'].where(bookings_expanded['delta'] >= 0.0001, 0)
    bookings_expanded.rename(columns={'delta': 'share'}, inplace=True)
    screen_and_log('Info: Positionen (shares) auf Tagesbasis erfolgreich aufgebaut', logfile, screen=screen)
    return bookings_expanded


def aggregate_banks(df):
    """Aggregiert die Werte in einem DataFrame mit MultiIndex (date, wkn, bank) über alle Banken"""
    expected_index = ['date', 'wkn', 'bank']
    if list(df.index.names) != expected_index:
        raise ValueError(f"Der DataFrame muss den MultiIndex {expected_index} haben.")
    df_aggregated = df.groupby(['date', 'wkn']).sum()
    return df_aggregated


def get_historical_price(ticker, date, logfile=None, screen=True):
    """Holt historischen Preis für ein bestimmtes Datum von yfinance"""
    try:
        if pd.isna(ticker) or str(ticker).strip() == '':
            return None
            
        ticker_clean = str(ticker).strip().upper()
        
        # Hole Daten für einen Tag vor und nach dem gewünschten Datum
        start_date = date - timedelta(days=5)
        end_date = date + timedelta(days=2)
        
        data = yf.download(ticker_clean, start=start_date, end=end_date, progress=False, auto_adjust=False)
        
        if data is None or data.empty or 'Close' not in data.columns:
            return None
            
        # Versuche das exakte Datum zu finden
        target_date = pd.Timestamp(date).normalize()
        if target_date in data.index:
            close_value = data.loc[target_date, 'Close']
            if isinstance(close_value, pd.Series):
                price_val = close_value.iloc[0]
            else:
                price_val = close_value
            
            # Konvertiere zu float, handle NaN und andere edge cases
            if pd.isna(price_val):
                return None
            try:
                return float(str(price_val))
            except (ValueError, TypeError):
                return None
        
        # Falls das exakte Datum nicht verfügbar ist, nimm den letzten verfügbaren Preis vor dem Datum
        available_dates = data.index[data.index <= target_date]
        if not available_dates.empty:
            last_available = available_dates.max()
            close_value = data.loc[last_available, 'Close']
            if isinstance(close_value, pd.Series):
                price_val = close_value.iloc[0]
            else:
                price_val = close_value
            
            # Konvertiere zu float, handle NaN und andere edge cases
            if pd.isna(price_val):
                return None
            try:
                return float(str(price_val))
            except (ValueError, TypeError):
                return None
            
        return None
        
    except Exception as e:
        if logfile:
            screen_and_log(f"Fehler beim Abrufen historischer Daten für {ticker}: {e}", logfile, screen)
        return None


def get_current_prices(instruments_df):
    """Holt aktuelle Preise für alle Instrumente"""
    prices = {}
    for wkn, row in instruments_df.iterrows():
        raw_ticker = row["ticker"]

        if pd.isna(raw_ticker):
            continue

        ticker = str(raw_ticker).strip().upper()
        if ticker == "":
            continue

        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=False)
            if data is not None and not data.empty and "Close" in data.columns:
                close_data = data["Close"]
                if not close_data.empty:
                    last_valid_price = float(close_data.dropna().iloc[-1].item())
                    prices[wkn] = last_valid_price
        except Exception as e:
            print(f"Fehler beim Abrufen von {ticker} für WKN {wkn}: {e}")
    return prices


def get_reference_values_from_yfinance(instruments_df, shares_yesterday, reference_date, logfile):
    """Berechnet Referenzwerte direkt von yfinance für ein bestimmtes Datum"""
    reference_values = {}
    
    for wkn in shares_yesterday.index:
        if wkn in instruments_df.index:
            ticker = instruments_df.loc[wkn, 'ticker']
            share_count = shares_yesterday.loc[wkn, 'share']
            
            if pd.notna(share_count) and share_count > 0:
                historical_price = get_historical_price(ticker, reference_date, logfile)
                if historical_price is not None:
                    reference_values[wkn] = {
                        'price': historical_price,
                        'value': historical_price * share_count,
                        'share': share_count
                    }
    
    return reference_values


# Main Block 01: Initializing    
def initializing(settings_file, screen):
    """Initialisiert das Programm"""
    error_count = 0
    warning_count = 0
    settings = None
    screen = True

    try:   
        set_working_directory("default", logfile=None, screen=screen)
        screen_and_log("Info: Arbeitsverzeichnis initial auf Ausführungsordner gesetzt.", logfile=None, screen=screen)
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Setzen des Arbeitsverzeichnisses: {e}", logfile=None, screen=screen)
        error_count += 1
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None

    settings = settings_import(settings_file)
    if settings is None:
        screen_and_log("ERROR: Einstellungen konnten nicht geladen werden.", logfile=None, screen=screen)
        error_count += 1
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None
    
    try:
        set_working_directory(settings['Paths']['path'], logfile=None, screen=screen)
        screen_and_log("Info: Arbeitsverzeichnis erfolgreich gesetzt.", logfile=None, screen=screen)
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Setzen des Arbeitsverzeichnisses: {e}", logfile=None, screen=screen)
        error_count += 1
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None

    logfile = settings['Files']['logfile']
    if logfile is None:
        logfile = 'logfile.txt'
        screen_and_log("ERROR: Kein Logfile angegeben. Fallback auf 'logfile.txt'.", logfile, screen=screen)

    if not os.path.exists(logfile):
        try:
            with open(logfile, 'w', encoding='utf-8') as log_file:
                log_file.write("")
            screen_and_log(f"Info: Logfile '{logfile}' wurde neu angelegt.", logfile, screen=screen)
        except Exception as e:
            screen_and_log(f"ERROR: Logfile '{logfile}' konnte nicht erstellt werden: {e}", logfile, screen=screen)
            error_count += 1

    # Nur Instruments und Bookings prüfen, prices.parquet wird nicht mehr benötigt
    required_files = [settings['Files']['instruments'], settings['Files']['bookings']]
    if not files_availability_check(required_files, logfile, screen=screen):
        screen_and_log("ERROR: Eine oder mehrere Dateien fehlen.", logfile, screen=screen)
        error_count += 1
    else:
        screen_and_log("Info: Alle Dateien verfügbar und erfolgreich geladen.", logfile, screen=screen)

    function_result("Initialisierung", error_count, warning_count, logfile, screen=screen)
    return settings


def instruments_import_and_process(settings, logfile, screen=True):
    """Importiert die Instruments-Datei"""
    try:
        instruments_file = settings['Files']['instruments']
        instruments_df = instruments_import(instruments_file, logfile, screen=screen)

        if instruments_df is None:
            screen_and_log(f"ERROR: Fehler beim Laden der Instruments-Datei '{instruments_file}'.", logfile, screen=screen)
            return None

        screen_and_log("Info: Instruments-Datei erfolgreich geladen.", logfile, screen=screen)
        return instruments_df

    except Exception as e:
        screen_and_log(f"ERROR: Unerwarteter Fehler beim Instruments-Import: {e}", logfile, screen=screen)
        return None


def bookings_import_and_process(settings, instruments_df, logfile, screen=True):
    """Importiert und prüft die Buchungsdaten"""
    error_count = 0
    warning_count = 0
    bookings_df = None

    try:
        bookings_file = settings['Files']['bookings']
        bookings_df = bookings_import(bookings_file, logfile, screen=screen)

        if bookings_df is None:
            screen_and_log(f"ERROR: Fehler beim Import der Buchungsdatei '{bookings_file}'.", logfile, screen=screen)
            error_count += 1
            function_result("Buchungen-Import und -Verarbeitung", error_count, warning_count, logfile, screen=screen)
            return None

        missing_wkns = bookings_check_for_instruments(bookings_df, instruments_df)
        if missing_wkns:
            screen_and_log(f"ERROR: WKNs aus Buchungen fehlen in Instruments: {missing_wkns}", logfile, screen=screen)
            error_count += 1
            function_result("Buchungen-Import und -Verarbeitung", error_count, warning_count, logfile, screen=screen)
            return None

        screen_and_log("Info: Alle WKNs aus Buchungen sind in Instruments vorhanden.", logfile, screen=screen)

    except Exception as e:
        screen_and_log(f"ERROR: Unerwarteter Fehler beim Einlesen der Buchungen: {e}", logfile, screen=screen)
        error_count += 1
        bookings_df = None

    function_result("Buchungen-Import und -Verarbeitung", error_count, warning_count, logfile, screen=screen)
    return bookings_df


def get_last_trading_day():
    """Bestimmt den letzten Handelstag (gestern oder der letzte Werktag)"""
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    
    # Deutsche Feiertage
    de_holidays = Germany()
    
    # Gehe bis zu 5 Tage zurück, um den letzten Handelstag zu finden
    for i in range(1, 6):
        check_date = today - timedelta(days=i)
        # Montag bis Freitag und kein Feiertag
        if check_date.weekday() < 5 and check_date.strftime('%Y-%m-%d') not in de_holidays:
            return pd.Timestamp(check_date)
    
    # Fallback auf gestern
    return pd.Timestamp(yesterday)


def get_last_trading_day_of_previous_month():
    """Bestimmt den letzten Handelstag des Vormonats"""
    today = datetime.today().date()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    
    de_holidays = Germany()
    
    # Gehe bis zu 10 Tage vom letzten Tag des Vormonats zurück
    for i in range(10):
        check_date = last_day_previous_month - timedelta(days=i)
        if check_date.weekday() < 5 and check_date.strftime('%Y-%m-%d') not in de_holidays:
            return pd.Timestamp(check_date)
    
    return None


def run_monitor(instruments_df, shares_yesterday, reference_date, logfile,
                values_last_month=None, shares_last_month=None, reference_date_month=None):
    """Hauptschleife für das Monitoring"""
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starte Kursabfrage...")
        current_prices = get_current_prices(instruments_df)
        
        # Hole Referenzdaten direkt von yfinance
        reference_data = get_reference_values_from_yfinance(instruments_df, shares_yesterday, reference_date, logfile)
        
        output_rows = []

        for wkn, price_today in current_prices.items():
            try:
                if wkn in reference_data:
                    ref_data = reference_data[wkn]
                    price_yesterday = ref_data['price']
                    share_count = ref_data['share']
                    
                    if share_count > 0:
                        diff_price = price_today - price_yesterday
                        percent_price = (diff_price / price_yesterday) * 100
                        diff_value = diff_price * share_count

                        # Monatliche Unterschiede falls verfügbar
                        diff_price_month = ""
                        percent_price_month = ""
                        diff_value_month = ""
                        
                        if reference_date_month is not None:
                            monthly_ref_data = get_reference_values_from_yfinance(
                                instruments_df, shares_yesterday, reference_date_month, logfile)
                            
                            if wkn in monthly_ref_data:
                                price_last_month = monthly_ref_data[wkn]['price']
                                diff_price_month = round(price_today - price_last_month, 2)
                                percent_price_month = round(((price_today - price_last_month) / price_last_month) * 100, 2)
                                diff_value_month = round((price_today - price_last_month) * share_count, 2)

                        instrument_name = instruments_df.loc[wkn, "instrument_name"] if wkn in instruments_df.index else wkn
                        output_rows.append({
                            "Name": instrument_name,
                            "Aktueller Preis": round(price_today, 2),
                            "Kursdiff": round(diff_price, 2),
                            "Kursdiff (%)": round(percent_price, 2),
                            "Wertdiff (€)": round(diff_value, 2),
                            "Kursdiff Monat": diff_price_month,
                            "Kursdiff Monat (%)": percent_price_month,
                            "Wertdiff Monat (€)": diff_value_month
                        })

            except Exception as e:
                print(f"WKN {wkn}: Fehler – {e}")

        df_out = pd.DataFrame(output_rows)

        # Summenzeile hinzufügen
        if not df_out.empty:
            gesamtwertdiff = df_out["Wertdiff (€)"].sum()
            
            gesamtwertdiff_month = ""
            if "Wertdiff Monat (€)" in df_out.columns:
                monthly_values = df_out["Wertdiff Monat (€)"]
                numeric_monthly = [val for val in monthly_values if isinstance(val, (int, float))]
                if numeric_monthly:
                    gesamtwertdiff_month = round(sum(numeric_monthly), 2)
            
            df_out.loc[len(df_out.index)] = {
                "Name": "SUMME",
                "Aktueller Preis": "",
                "Kursdiff": "",
                "Kursdiff (%)": "",
                "Wertdiff (€)": round(gesamtwertdiff, 2),
                "Kursdiff Monat": "",
                "Kursdiff Monat (%)": "",
                "Wertdiff Monat (€)": gesamtwertdiff_month
            }

        # JSON-Struktur mit Referenzdaten erstellen
        json_data = {
            "reference_date": reference_date.strftime('%d.%m.%Y'),
            "reference_date_month": reference_date_month.strftime('%d.%m.%Y') if reference_date_month is not None else "",
            "data": df_out.to_dict('records')
        }
        
        with open("static/depotdaten.json", 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"Kursdifferenz bezogen auf Schlusskurs vom: {reference_date.strftime('%d.%m.%Y')}")
        if reference_date_month is not None:
            print(f"Monatliche Kursdifferenz bezogen auf Schlusskurs vom: {reference_date_month.strftime('%d.%m.%Y')}")
        print(df_out.to_string(index=False))

        intervall = 10  # 10 Sekunden für Tests, später auf 600 (10 Minuten) ändern
        print(f"→ Daten aktualisiert. Nächste Abfrage in {intervall} Sekunden.")
        time.sleep(intervall)


def main():
    settings = initializing("status.ini", screen=False)
    if settings is None:
        print("Error: Could not initialize settings")
        return
        
    logfile = settings.get("Files", {}).get("logfile")
    screen = settings.get("Output", {}).get("screen", True)

    # Nur Instruments und Bookings laden - keine Preise mehr!
    instruments_df = instruments_import_and_process(settings, logfile, screen=screen)
    bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=screen)

    if instruments_df is None or bookings_df is None:
        print("Error: Could not load required data")
        return

    # Bestimme das Ende der Buchungsdaten (heute)
    end_date = pd.Timestamp(datetime.today().date())
    
    # Erstelle Shares-DataFrame
    shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=screen)
    if shares_day_banks_df is None:
        print("Error: Could not process bookings data")
        return
        
    shares_day_df = aggregate_banks(shares_day_banks_df)

    # Bestimme Referenzdaten
    last_trading_day = get_last_trading_day()
    shares_yesterday = shares_day_df.loc[last_trading_day] if last_trading_day in shares_day_df.index else None
    
    if shares_yesterday is None:
        print("Error: No shares data available for reference date")
        return

    # Monatliche Referenzdaten
    last_trading_day_prev_month = get_last_trading_day_of_previous_month()

    print(f"Starte Monitoring mit Referenzdatum: {last_trading_day.strftime('%d.%m.%Y')}")
    if last_trading_day_prev_month is not None:
        print(f"Monatliches Referenzdatum: {last_trading_day_prev_month.strftime('%d.%m.%Y')}")

    # Starte Monitoring
    run_monitor(instruments_df, shares_yesterday, last_trading_day, logfile,
                reference_date_month=last_trading_day_prev_month)


if __name__ == "__main__":
    main()