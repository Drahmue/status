"""Test script to check shares_day_df date range"""
import pandas as pd
from datetime import datetime, timedelta
from status import (
    initializing,
    instruments_import_and_process,
    bookings_import_and_process,
    shares_from_bookings,
    aggregate_banks,
    get_last_trading_day
)

# Initialize
settings = initializing("status.ini", screen=True)
if settings is None:
    print("ERROR: Could not initialize")
    exit(1)

logfile = settings.get("Files", {}).get("logfile")

# Load data
instruments_df = instruments_import_and_process(settings, logfile, screen=True)
bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=True)

if instruments_df is None or bookings_df is None:
    print("ERROR: Could not load data")
    exit(1)

# Create shares DataFrame
end_date = pd.Timestamp(datetime.today().date()) + timedelta(days=30)
print(f"\nEnd date for shares: {end_date.strftime('%d.%m.%Y')}")

shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=True)
shares_day_df = aggregate_banks(shares_day_banks_df)

print(f"\nShares DataFrame date range:")
print(f"  Min date: {shares_day_df.index.get_level_values('date').min().strftime('%d.%m.%Y')}")
print(f"  Max date: {shares_day_df.index.get_level_values('date').max().strftime('%d.%m.%Y')}")
print(f"  Total days: {len(shares_day_df.index.get_level_values('date').unique())}")

# Check for last trading day
last_trading_day = get_last_trading_day()
print(f"\nLetzter Handelstag: {last_trading_day.strftime('%d.%m.%Y')}")
print(f"Ist {last_trading_day.strftime('%d.%m.%Y')} in shares_day_df? {last_trading_day in shares_day_df.index.get_level_values('date')}")

if last_trading_day in shares_day_df.index.get_level_values('date'):
    print(f"Shares-Daten für {last_trading_day.strftime('%d.%m.%Y')} verfügbar!")
else:
    print(f"FEHLER: Keine Shares-Daten für {last_trading_day.strftime('%d.%m.%Y')}!")

    # Find closest date
    all_dates = shares_day_df.index.get_level_values('date').unique()
    dates_before = [d for d in all_dates if d <= last_trading_day]
    if dates_before:
        closest = max(dates_before)
        print(f"Nächstes verfügbares Datum: {closest.strftime('%d.%m.%Y')}")
