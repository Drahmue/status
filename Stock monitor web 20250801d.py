import pandas as pd
import yfinance as yf
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import importlib
import holidays
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


# ALLGEMEINE FUNKTIONEN

# Standardbiblithek einbinden

# Pfad zur Standardbibliothek
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
    from Standardfunktionen_aktuell import *
    print(f"Import der Bibliothek: {library_name} von {standard_library_path} erfolgreich")
except ImportError as e:
    sys.exit(f"Fehler beim Import der Bibliothek: {e}")


def function_result(function_name, error_count, warning_count, logfile, screen=True):
    """
    Überprüft die Rückgabewerte einer Funktion und gibt eine entsprechende Meldung aus.
    Beendet das Programm, wenn Fehler aufgetreten sind.

    Parameter:
        function_name (str): Der Name der aufgerufenen Funktion.
        error_count (int): Anzahl der aufgetretenen Fehler.
        warning_count (int): Anzahl der aufgetretenen Warnungen.
        logfile (str): Der Name des Logfiles.
        screen (bool): Wenn True, werden Bildschirmmeldungen angezeigt.
        log (bool): Wenn True, werden Meldungen ins Logfile geschrieben.
    """
    # Überprüfung der Rückgabewerte für Fehler und Warnugen
    if error_count > 0:
        screen_and_log(f"ERROR: {function_name} fehlgeschlagen. Das Programm wird beendet.", logfile, screen=True)
        sys.exit(1)
    elif warning_count > 0:
        screen_and_log(f"WARNING: {function_name} abgeschlossen mit {warning_count} Warnung(en).", logfile, screen=True)
    else:
        screen_and_log(f"Info: {function_name} erfolgreich abgeschlossen.", logfile, screen=True)




# Spezifische Funktionen
# Funktion die aus dem instruments file (EXCEL) die Schlüssel wkn, ticker, Name und Default Wert lädet
def instruments_import(filename, logfile, screen=True):
    """
    Liest die Excel-Datei und importiert die ersten vier Spalten (wkn, ticker, instrument_name, Default)
    in einen Pandas DataFrame. wkn und ticker werden in Kleinbuchstaben umgewandelt.
    wkn wird als Index gesetzt. Spaltennamen werden auf 'ticker', 'Name', 'default_value' gesetzt.
    
    Fehlerabfrage: Wenn die Datei kein Excel-Format hat oder ein anderer Fehler auftritt, wird eine Meldung ausgegeben.
    """
    try:
        # Prüfe, ob die Datei eine Excel-Datei ist
        if not filename.endswith(('.xlsx', '.xls')):
            raise ValueError(f"Die Datei '{filename}' ist keine Excel-Datei.")

        # Lese die ersten vier Spalten aus der Excel-Datei und setze die erste Spalte (wkn) als Index
        df = pd.read_excel(filename, usecols=[0, 1, 2, 3], index_col=0)

        # Wandle den Index (wkn) und die ticker-Spalte in Kleinbuchstaben um
        df.index = df.index.str.lower()  # wkn auf Kleinbuchstaben umstellen
        df['ticker'] = df['ticker'].str.lower()  # ticker auf Kleinbuchstaben umstellen

        # Setze die Spaltennamen sicher
        df.columns = ['ticker', 'instrument_name', 'default_value']  # Sichere Zuweisung der Spaltennamen

        # Gib den DataFrame zurück
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
       
# Funktion zum gegenseitigen Abgleich ob alle wkn in prices und instrumentes enthalten sind
def prices_check_for_instruments(prices, instruments, logfile, screen=True):
    """
    Überprüft, ob alle WKNs aus 'prices' im DataFrame 'instruments' vorhanden sind und umgekehrt.
    
    Parameter:
        prices (DataFrame): Der DataFrame mit Preis-Daten.
        instruments (DataFrame): Der DataFrame mit Instruments-Daten.
        logfile (str): Der Name des Logfiles.
        screen (bool): Wenn True, werden Bildschirmmeldungen angezeigt.
        log (bool): Wenn True, werden Meldungen ins Logfile geschrieben.
    """
    wkn_prices = set(prices.index.get_level_values('wkn'))
    wkn_instruments = set(instruments.index)

    missing_in_instruments = wkn_prices - wkn_instruments
    if missing_in_instruments:
        screen_and_log(f"WARNING: Die folgenden WKNs aus 'prices' fehlen in 'instruments': {missing_in_instruments}", logfile, screen=screen)
    else:
        screen_and_log("Info: Alle WKNs aus 'prices' sind in 'instruments' vorhanden.", logfile, screen=screen)

    missing_in_prices = wkn_instruments - wkn_prices
    if missing_in_prices:
        screen_and_log(f"WARNING: Die folgenden WKNs aus 'instruments' fehlen in 'prices': {missing_in_prices}", logfile, screen=screen)
    else:
        screen_and_log("Info: Alle WKNs aus 'instruments' sind in 'prices' vorhanden.", logfile, screen=screen)

# Funktion zum Aktualisieren der Kursdaten zwischen last_date und gestern
def prices_update(prices, instruments, logfile, screen=True):
    """
    Aktualisiert fehlende Kursdaten in 'prices' zwischen dem letzten Datum und gestern,
    wobei nur Handelstage (Mo–Fr, ohne Feiertage) berücksichtigt werden.
    
    Parameter:
        prices (DataFrame): Bestehende Kursdaten. MultiIndex ('date', 'wkn'), Spalte 'price'
        instruments (DataFrame): Enthält je WKN einen 'ticker' und optional 'default_value'
        logfile (str): Pfad zur Logdatei
        screen (bool): Gibt Statusmeldungen auf dem Bildschirm aus, falls True

    Rückgabe:
        DataFrame: Aktualisierter 'prices'-DataFrame
    """
    # Aktuelles Datum (nur ohne Uhrzeit)
    today = datetime.today().date()
    yesterday = pd.Timestamp(today - timedelta(days=1))

    # Letztes verfügbares Datum im DataFrame
    last_date = prices.index.get_level_values('date').max()

    # Deutsche Feiertage
    de_holidays = holidays.Germany()

    # Datumsbereich: alle Kalendertage zwischen letztem Kursdatum und gestern
    all_dates = pd.date_range(start=last_date + timedelta(days=1), end=yesterday)

    # Nur Mo–Fr und keine Feiertage
    missing_dates = [d for d in all_dates if d.weekday() < 5 and d.strftime('%Y-%m-%d') not in de_holidays]

    if not missing_dates:
        screen_and_log(
            f"Info: Keine fehlenden Handelstage zwischen {last_date.date()} und {yesterday.date()}",
            logfile, screen=screen
        )
        return prices

    # Für jede WKN einzeln Kursdaten abrufen
    for wkn, row in instruments.iterrows():
        #ticker = row['ticker']
        raw_ticker = row['ticker']

        # Erst prüfen, ob NaN oder leer
        if pd.isna(raw_ticker) or str(raw_ticker).strip() == '':
            ticker = None
        else:
            ticker = str(raw_ticker).strip().upper()

        
        default_value = row['default_value']
        #print(wkn, "Defalut Value", default_value) #debug
        

        if pd.notna(ticker) and ticker.strip() != '':
            try:
                data = yf.download(
                    ticker,
                    start=missing_dates[0],
                    end=missing_dates[-1] + timedelta(days=1),  # Enddatum exklusiv
                    progress=False,
                    auto_adjust=False
                )

                if data.empty:
                    screen_and_log(
                        f"WARNING: Keine Daten für Ticker {ticker} im Zeitraum {missing_dates[0].date()} bis {missing_dates[-1].date()}",
                        logfile, screen=screen
                    )
                    continue

                # Stelle sicher, dass der Index normiert ist
                data.index = data.index.normalize()

                for date in missing_dates:
                    normalized_date = pd.Timestamp(date).normalize()

                    try:
                        # Versuche Zugriff auf 'Close'-Wert
                        close_entry = data.loc[normalized_date, 'Close']

                        # Falls Series: z. B. durch mehrdimensionale Struktur
                        if isinstance(close_entry, pd.Series):
                            close_value = close_entry.iloc[0]
                        else:
                            close_value = close_entry

                        prices.loc[(normalized_date, wkn), 'price'] = close_value

                    except KeyError:
                        prices.loc[(normalized_date, wkn), 'price'] = np.nan
                        screen_and_log(
                            f"WARNING: Kein Kurs für {ticker} am {normalized_date.date()} verfügbar",
                            logfile, screen=screen
                        )

                    except Exception as e:
                        screen_and_log(
                            f"ERROR: Unerwarteter Fehler bei Zugriff auf Close-Wert {ticker} am {normalized_date.date()}: {e}",
                            logfile, screen=screen
                        )

            except Exception as e:
                screen_and_log(
                    f"ERROR: Fehler beim Abrufen der Daten am {missing_dates[0]} für WKN {wkn} ({ticker}): {e}",
                    logfile, screen=screen
                )

        else:
            # Kein Ticker → Defaultwert setzen
            for date in missing_dates:
                normalized_date = pd.Timestamp(date).normalize()
                prices.loc[(normalized_date, wkn), 'price'] = float(default_value) if default_value is not None else np.nan

    return prices

# Funktion zum Einlesen der Buchungsdaten
def bookings_import(filename, logfile, screen=True):
    try:
        # Lese die ersten vier Spalten aus der Excel-Datei
        df = pd.read_excel(filename, usecols=[0, 1, 2, 3], names=['date', 'wkn', 'bank', 'delta'])
        
        # Konvertiere 'wkn' und 'bank' in Kleinbuchstaben
        df['wkn'] = df['wkn'].str.lower()
        df['bank'] = df['bank'].str.lower()
        
        # Entferne Zeilen mit NaN in 'wkn', 'bank' oder 'delta'
        df.dropna(subset=['wkn', 'bank', 'delta'], inplace=True)
        
        # Setze den MultiIndex auf 'date', 'wkn', 'bank'
        df.set_index(['date', 'wkn', 'bank'], inplace=True)
        
        # Fasse Einträge mit demselben MultiIndex zusammen und summiere 'delta'
        # Damit werden mehrere Transaktion an einem Tag für eine WKN (bei der gleichen bank) zu einem Eintrag kombiniert
        df = df.groupby(level=['date', 'wkn', 'bank']).sum()
        
        return df

    except FileNotFoundError:
        screen_and_log(f"Fehler: Die Datei '{filename}' wurde nicht gefunden.", logfile, screen=screen)
        return None
    except Exception as e:
        screen_and_log(f"Ein Fehler ist beim Import der Buchungen aus '{filename}' aufgetreten: {e}", logfile, screen=screen)
        return None

# Funktion zum Prüfung ob alle WKN in Buchungsdaten in Instruments gelistet sind
def bookings_check_for_instruments(bookings, instruments):
    """
    Überprüft, ob alle wkns aus 'bookings' im DataFrame 'instruments' vorhanden sind und gibt eine Liste fehlender wkns zurück.
    
    Parameter:
        bookings (DataFrame): Der DataFrame mit Buchungsdaten, der eine wkn-Spalte oder -Index enthalten muss.
        instruments (DataFrame): Der DataFrame mit Instrumenten-Daten, der eine wkn-Spalte oder -Index enthalten muss.
        
    Rückgabe:
        missing_in_instruments (list): Liste der wkns aus 'bookings', die nicht in 'instruments' enthalten sind.
    """
    # Extrahiere die wkns aus dem bookings DataFrame
    wkn_bookings = set(bookings.index.get_level_values('wkn'))
    wkn_instruments = set(instruments.index)

    # Erstelle die Liste der wkns in bookings, die in instruments fehlen
    missing_in_instruments = list(wkn_bookings - wkn_instruments)
    
    return missing_in_instruments

# Funktion zur Umsetzung der Buchungen in ein Bestandsfile für alle Tage
def shares_from_bookings(bookings, end_date, logfile, screen=False):
    """
    Erweitert den DataFrame `bookings` mit allen Kombinationen von Datum, wkn und Bank
    bis zu einem angegebenen Enddatum und berechnet die laufende Summe.
    debei bedeutet share die Anzahl der Anteile für eine WKN an

    Parameter:
        bookings (DataFrame): Ein DataFrame mit MultiIndex (date, wkn, bank) und einer Spalte 'delta'.
        end_date (datetime): Das Datum, bis zu dem der DataFrame aufgebaut werden soll.

    Rückgabe:
        DataFrame: Ein erweiterter DataFrame mit dem MultiIndex (date, wkn, bank) und der laufenden Summe in der Spalte 'share'.
    """
    # Bestimme das vollständige Datumsspektrum bis zum übergebenen Enddatum
    all_dates = pd.date_range(bookings.index.get_level_values('date').min(), end_date)
    wkns = bookings.index.get_level_values('wkn').unique()
    banks = bookings.index.get_level_values('bank').unique()
    
    # Erstelle einen vollständigen MultiIndex für Datum, wkn und Bank
    full_index = pd.MultiIndex.from_product([all_dates, wkns, banks], names=['date', 'wkn', 'bank'])
    
    # Reindexiere den DataFrame, um alle Kombinationen von Datum, wkn und Bank abzudecken, und fülle NaN mit 0
    bookings_expanded = bookings.reindex(full_index).fillna(0)
    
    # Berechne die laufende Summe über das Datum für jede Kombination von wkn und Bank
    bookings_expanded['delta'] = bookings_expanded.groupby(['wkn', 'bank'])['delta'].cumsum()
    
    # Setze alle Werte kleiner als 0.0001 auf 0
    bookings_expanded['delta'] = bookings_expanded['delta'].where(bookings_expanded['delta'] >= 0.0001, 0)
    
    # Benenne die Spalte 'delta' in 'share' um
    bookings_expanded.rename(columns={'delta': 'share'}, inplace=True)

    screen_and_log('Info: Positionen (shares) auf Tagesbasis erfolgreich aufgebaut', logfile, screen=screen)
    
    return bookings_expanded

# Funktion zur Berechnung der Wertbestände values (pro WKN) aus den Beständen shares (Stück) und Kursen prices
def values_from_shares_and_prices(shares_day_banks, prices):
    """
    Multipliziert die Positionen und Preise für jeden Indexwert (date, wkn, bank) und gibt das Ergebnis zurück.
    
    Parameter:
        shares_day_banks (DataFrame): DataFrame mit MultiIndex (date, wkn, bank) und einer 'share' Spalte.
        prices (DataFrame): DataFrame mit MultiIndex (date, wkn) und einer 'price' Spalte.
        
    Rückgabe:
        values (DataFrame): DataFrame mit MultiIndex (date, wkn, bank) und dem Ergebnis der Multiplikation 'value'.
    """
    # Erweitere den prices DataFrame um den Index 'bank'
    banks = shares_day_banks.index.get_level_values('bank').unique()
    prices_expanded = prices.reindex(pd.MultiIndex.from_product(
        [prices.index.get_level_values('date').unique(),
         prices.index.get_level_values('wkn').unique(),
         banks],
        names=['date', 'wkn', 'bank']
    ))

    # Multipliziere die Werte in 'share' und 'price' für jeden Indexwert
    values = shares_day_banks.copy()
    values['value'] = values['share'] * prices_expanded['price']

    return values[['value']]

# Transformiert 3D Datafram mit Multiindex (date, wkn, bank) in 2D Dataframe (date, wkn)
def aggregate_banks(df):
    """
    Aggregiert die Werte in einem DataFrame mit MultiIndex (date, wkn, bank) über alle Banken
    für jede Kombination von date und wkn.

    Parameter:
        df (DataFrame): Ein DataFrame mit MultiIndex (date, wkn, bank) und den aggregierbaren Werten.

    Rückgabe:
        DataFrame: Aggregierter DataFrame mit MultiIndex (date, wkn) und den aggregierten Werten.
    """
    # Prüfe, ob der DataFrame den erwarteten MultiIndex (date, wkn, bank) hat
    expected_index = ['date', 'wkn', 'bank']
    if list(df.index.names) != expected_index:
        raise ValueError(f"Der DataFrame muss den MultiIndex {expected_index} haben.")

    # Aggregiere die Werte für jede Kombination von date und wkn über alle Banken
    df_aggregated = df.groupby(['date', 'wkn']).sum()

    return df_aggregated



    
# Main Block 01: Initializing    
def initializing(settings_file, screen):
    """
    Initialisiert das Programm, indem das Arbeitsverzeichnis gesetzt wird, die Einstellungen geladen werden
    und die Verfügbarkeit der erforderlichen Dateien überprüft wird.

    Parameter:
        screen (bool): Wenn True, werden Bildschirmmeldungen angezeigt.
        log (bool): Wenn True, werden Meldungen ins Logfile geschrieben.

    Rückgabe:
        settings (dict): Ein Dictionary mit den Programmeinstellungen oder None bei Fehler.
    """
    error_count = 0
    warning_count = 0
    settings = None
    screen = True # Debug   

    # 1. Arbeitsverzeichnis setzen, kann auch einen benutzerdefinierten Pfad akzeptieren
    try:   
        set_working_directory("default",logfile=None,screen=screen)
        screen_and_log("Info: Arbeitsverzeichnis initial auf Ausführungsordner gesetzt.",logfile=None,screen=screen) # Logfile noch nicht initialisiert 
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Setzen des Arbeitsverzeichnisses: {e}",logfile=None,screen=screen) # Logfile noch nicht initialisiert
        error_count += 1
        # Fehlerergebnis melden und beenden
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None

    # 2. Einstellungen aus der Datei 'depot_file_settings.txt' lesen
    settings = settings_import(settings_file)
    if settings is None:
        screen_and_log("ERROR: Einstellungen konnten nicht geladen werden.",logfile=None,screen=screen) # Logfile noch nicht initialisiert
        error_count += 1
        # Fehlerergebnis melden und beenden
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None
    
    # 3. Arbeitsverzeichnis auf Einstellung aus Settings setzen
    try:
        set_working_directory(settings['Paths']['path'],logfile=None,screen=screen)
        screen_and_log("Info: Arbeitsverzeichnis erfolgreich gesetzt.",logfile=None,screen=screen) # Logfile noch nicht initialisiert
    except Exception as e:
        screen_and_log(f"ERROR: Fehler beim Setzen des Arbeitsverzeichnisses: {e}",logfile=None,screen=screen) # Logfile noch nicht initialisiert
        error_count += 1
        # Fehlerergebnis melden und beenden
        function_result("Initialisierung", error_count, warning_count, logfile=None, screen=screen)
        return None

    # 4.1. Logfile-Pfad aus den Einstellungen extrahieren
    logfile = settings['Files']['logfile']
    
    # 4.2. Prüfen, ob logfile None ist, und ggf. auf Standard setzen
    if logfile is None:
        logfile = 'logfile.txt'
        screen_and_log("ERROR: Kein Logfile angegeben. Fallback auf 'logfile.txt'.", logfile, screen=screen)

    # 4.3. Prüfen, ob logfile existiert; wenn nicht, die Datei mit UTF-8 anlegen
    if not os.path.exists(logfile):
        try:
            with open(logfile, 'w', encoding='utf-8') as log_file:
                log_file.write("")  # Leere Datei anlegen
            screen_and_log(f"Info: Logfile '{logfile}' wurde neu angelegt.", logfile, screen=screen)
        except Exception as e:
            screen_and_log(f"ERROR: Logfile '{logfile}' konnte nicht erstellt werden: {e}", logfile, screen=screen)
            error_count += 1



    # 5. Überprüfen, ob die erforderlichen Dateien verfügbar sind
    file_list = list(settings['Files'].values())
    if not files_availability_check(file_list, logfile, screen=screen):
        screen_and_log("ERROR: Eine oder mehrere Dateien fehlen.", logfile, screen=screen)
        error_count += 1
    else:
        screen_and_log("Info: Alle Dateien verfügbar und erfolgreich geladen.", logfile, screen=screen)

    # Aufruf von function_result vor der Rückgabe
    function_result("Initialisierung", error_count, warning_count, logfile, screen=screen)
    return settings

# Main Block 02: Instrumente importieren
def instruments_import_and_process(settings, logfile, screen=True):
    """
    Importiert die Instruments-Datei und gibt ein DataFrame zurück.
    """
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

# Main Block 03: Kurse (prices) importieren, prüfen und updaten
def prices_import_and_process(settings, instruments_df, logfile, screen=True):
    """
    Importiert und verarbeitet Preisdaten:
    - liest die Preisdatei ein,
    - gleicht mit den Instrumenten ab,
    - ergänzt fehlende (Datum, WKN)-Kombis mit NaN,
    - füllt fehlende Preise per forward fill auf.

    Rückgabe:
        DataFrame mit verarbeiteten Kursdaten oder None bei Fehlern.
    """
    error_count = 0
    warning_count = 0

    try:
        prices_file = settings['Files']['prices']
        prices_df = import_parquet(prices_file, logfile, screen=screen)

        if prices_df is None:
            screen_and_log(f"ERROR: Fehler beim Einlesen der Kursdatei '{prices_file}'.", logfile, screen=screen)
            function_result("Kursdaten-Import", 1, 0, logfile, screen=screen)
            return None

        prices_check_for_instruments(prices_df, instruments_df, logfile, screen=screen)
        prices_df = prices_update(prices_df, instruments_df, logfile, screen=screen)

        # Ergänzen aller (Datum, WKN)-Kombinationen
        try:
            today = datetime.today().date()
            yesterday = pd.Timestamp(today - timedelta(days=1))
            all_dates = pd.date_range(prices_df.index.get_level_values('date').min(), yesterday, freq='D')
            all_wkns = prices_df.index.get_level_values('wkn').unique()
            full_index = pd.MultiIndex.from_product([all_dates, all_wkns], names=['date', 'wkn'])
            prices_df = prices_df.reindex(full_index)
            screen_and_log("Info: Fehlende (Datum, WKN)-Kombis ergänzt mit NaN.", logfile, screen=screen)
        except Exception as e:
            warning_count += 1
            screen_and_log(f"WARNING: Ergänzen fehlender Indizes fehlgeschlagen: {e}", logfile, screen=screen)

        # Forward fill je WKN
        try:
            prices_df = prices_df.sort_index(level='date')
            prices_df['price'] = prices_df.groupby('wkn')['price'].ffill()
            screen_and_log("Info: Fehlende Preise per ffill ergänzt.", logfile, screen=screen)
        except Exception as e:
            warning_count += 1
            screen_and_log(f"WARNING: Fehler bei ffill der Preise: {e}", logfile, screen=screen)

    except Exception as e:
        error_count += 1
        screen_and_log(f"ERROR: Unerwarteter Fehler beim Import der Kursdaten: {e}", logfile, screen=screen)
        return None

    function_result("Kursdaten-Import und -Verarbeitung", error_count, warning_count, logfile, screen=screen)
    return prices_df

# Main Block 04: Buchungen (bookings) importieren
def bookings_import_and_process(settings, instruments_df, logfile, screen=True):
    """
    Importiert und prüft die Buchungsdaten:
    - liest die Buchungsdatei ein,
    - prüft, ob alle WKNs in den Instrumenten enthalten sind.

    Rückgabe:
        DataFrame mit Buchungsdaten oder None bei Fehlern.
    """
    error_count = 0
    warning_count = 0

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

    function_result("Buchungen-Import und -Verarbeitung", error_count, warning_count, logfile, screen=screen)
    return bookings_df


def get_yesterday():
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    return pd.Timestamp(yesterday)

def get_current_prices(instruments_df):
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
            if not data.empty:
                last_valid_price = float(data["Close"].dropna().iloc[-1].item())
                prices[wkn] = last_valid_price
        except Exception as e:
            print(f"Fehler beim Abrufen von {ticker} für WKN {wkn}: {e}")
    return prices

def run_monitor(instruments_df, values_yesterday, shares_yesterday):
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starte Kursabfrage...")
        current_prices = get_current_prices(instruments_df)
        output_rows = []

        for wkn, price_today in current_prices.items():
            try:
                if wkn in values_yesterday.index and wkn in shares_yesterday.index:
                    value_yest = values_yesterday.loc[wkn, 'value']
                    share_yest = shares_yesterday.loc[wkn, 'share']
                    if pd.notna(share_yest) and share_yest > 0 and pd.notna(value_yest) and value_yest > 0:
                        price_yest = value_yest / share_yest
                        diff_price = price_today - price_yest
                        percent_price = (diff_price / price_yest) * 100
                        diff_value = diff_price * share_yest

                        instrument_name = instruments_df.loc[wkn, "instrument_name"] if wkn in instruments_df.index else wkn
                        output_rows.append({
                            "Name": instrument_name,
                            "Aktueller Preis": round(price_today, 2),
                            "Kursdiff": round(diff_price, 2),
                            "Kursdiff (%)": round(percent_price, 2),
                            "Wertdiff (€)": round(diff_value, 2)
                        })

                # keine else-Verzweigung – keine Ausgabe bei share=0 oder value=0
            except Exception as e:
                print(f"WKN {wkn}: Fehler – {e}")

        df_out = pd.DataFrame(output_rows)

        # Summenzeile hinzufügen
        if not df_out.empty:
            gesamtwertdiff = df_out["Wertdiff (€)"].sum()
            df_out.loc[len(df_out.index)] = {
                "Name": "SUMME",
                "Aktueller Preis": "",
                "Kursdiff": "",
                "Kursdiff (%)": "",
                "Wertdiff (€)": round(gesamtwertdiff, 2)
            }

        df_out.to_json("static/depotdaten.json", orient="records", force_ascii=False, indent=2)
        print(df_out.to_string(index=False))


        intervall = 10  # 10 Minuten
        print(f"→ Daten aktualisiert. Nächste Abfrage in {intervall} Sekunden.")
        time.sleep(intervall)

def main():
    settings = initializing("kursabfrage_settings.ini", screen=False)
    logfile = settings["Files"]["logfile"]
    screen = settings["Output"]["screen"]

    instruments_df = instruments_import_and_process(settings, logfile, screen=screen)
    prices_df = prices_import_and_process(settings, instruments_df, logfile, screen=screen)
    bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=screen)

    end_date = prices_df.index.get_level_values("date").max()
    shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=screen)
    values_day_banks_df = values_from_shares_and_prices(shares_day_banks_df, prices_df)
    values_day_df = aggregate_banks(values_day_banks_df)
    shares_day_df = aggregate_banks(shares_day_banks_df)

    yesterday = get_yesterday()
    values_yesterday = values_day_df.loc[yesterday]
    shares_yesterday = shares_day_df.loc[yesterday]

    run_monitor(instruments_df, values_yesterday, shares_yesterday)

if __name__ == "__main__":
    main()