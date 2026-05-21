"""Test index check logic"""
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
settings = initializing("status.ini", screen=False)
logfile = settings.get("Files", {}).get("logfile")

# Load data
instruments_df = instruments_import_and_process(settings, logfile, screen=False)
bookings_df = bookings_import_and_process(settings, instruments_df, logfile, screen=False)

# Create shares DataFrame
end_date = pd.Timestamp(datetime.today().date()) + timedelta(days=30)
shares_day_banks_df = shares_from_bookings(bookings_df, end_date, logfile, screen=False)
shares_day_df = aggregate_banks(shares_day_banks_df)

last_trading_day = get_last_trading_day()

print(f"shares_day_df Index Namen: {shares_day_df.index.names}")
print(f"shares_day_df Index Typ: {type(shares_day_df.index)}")
print(f"\nLetzter Handelstag: {last_trading_day}")
print(f"Typ: {type(last_trading_day)}")

# Check different ways
print(f"\nTest 1 - 'last_trading_day in shares_day_df.index':")
print(f"  Result: {last_trading_day in shares_day_df.index}")

print(f"\nTest 2 - 'last_trading_day in shares_day_df.index.get_level_values(\"date\")':")
print(f"  Result: {last_trading_day in shares_day_df.index.get_level_values('date')}")

print(f"\nTest 3 - Try to access shares_yesterday:")
try:
    shares_yesterday = shares_day_df.loc[last_trading_day]
    print(f"  SUCCESS! Type: {type(shares_yesterday)}")
    print(f"  Shape: {shares_yesterday.shape if hasattr(shares_yesterday, 'shape') else 'N/A'}")
    print(f"  Content (first 3 rows):")
    print(shares_yesterday.head(3))
except Exception as e:
    print(f"  ERROR: {e}")

print(f"\nTest 4 - Conditional access (wie im Code):")
shares_yesterday = shares_day_df.loc[last_trading_day] if last_trading_day in shares_day_df.index else None
print(f"  Result: {type(shares_yesterday) if shares_yesterday is not None else 'None'}")
if shares_yesterday is None:
    print("  ERROR: shares_yesterday ist None!")
