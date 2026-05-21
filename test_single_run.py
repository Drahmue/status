"""Test single monitoring run without while loop"""
from status import (initializing, instruments_import_and_process,
                     bookings_import_and_process, shares_from_bookings,
                     aggregate_banks, get_last_trading_day, get_current_prices)
from datetime import datetime, timedelta
import pandas as pd

print('=== Test: Einzelner Monitoring-Durchlauf ===')
print('')

# Initialize
settings = initializing('status.ini', screen=False)
logfile = settings.get('Files', {}).get('logfile')

# Load data
instruments_df = instruments_import_and_process(settings, logfile, screen=False)
bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=False)

# Create shares
end_date = pd.Timestamp(datetime.today().date()) + timedelta(days=30)
shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=False)
shares_day_df = aggregate_banks(shares_day_banks_df)

# Get reference date
last_trading_day = get_last_trading_day()
print(f'Letzter Handelstag: {last_trading_day.strftime("%d.%m.%Y")}')

shares_yesterday = shares_day_df.loc[last_trading_day] if last_trading_day in shares_day_df.index.get_level_values('date') else None
print(f'Shares verfügbar: {"Ja" if shares_yesterday is not None else "NEIN"}')

# CRITICAL: Try to get current prices
print('')
print('Hole aktuelle Kurse (dies kann hängen bei API-Problemen)...')
import time
start_time = time.time()

try:
    current_prices = get_current_prices(instruments_df)
    elapsed = time.time() - start_time
    print(f'Kurse abgerufen: {len(current_prices)} Instrumente in {elapsed:.1f} Sekunden')

    # Show first 3 prices
    for i, (wkn, price) in enumerate(list(current_prices.items())[:3]):
        print(f'  {wkn}: {price}')

except Exception as e:
    elapsed = time.time() - start_time
    print(f'FEHLER nach {elapsed:.1f} Sekunden: {e}')

print('')
print('Test abgeschlossen!')
