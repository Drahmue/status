from datetime import datetime, timedelta
from holidays.countries.germany import Germany
import pandas as pd

today = datetime.today().date()
de_holidays = Germany()

print(f"Heute: {today} ({today.strftime('%d.%m.%Y')})")
print(f"Wochentag heute: {today.weekday()} (0=Montag, 6=Sonntag)")
print()

print("Checking last 10 days:")
for i in range(1, 11):
    check_date = today - timedelta(days=i)
    is_holiday = check_date.strftime('%Y-%m-%d') in de_holidays
    is_weekday = check_date.weekday() < 5
    is_trading_day = is_weekday and not is_holiday

    print(f"{check_date.strftime('%d.%m.%Y')} (Wochentag {check_date.weekday()}): "
          f"Werktag={is_weekday}, Kein Feiertag={not is_holiday}, "
          f"Handelstag={is_trading_day}")

print()
print("Testing get_last_trading_day() function:")

def get_last_trading_day():
    """Bestimmt den letzten Handelstag (gestern oder der letzte Werktag)"""
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # Deutsche Feiertage
    de_holidays = Germany()

    # Gehe bis zu 5 Tage zurück, um den letzten Handelstag zu finden
    for i in range(1, 6):
        check_date = today - timedelta(days=i)
        print(f"  Prüfe: {check_date.strftime('%d.%m.%Y')} - Wochentag: {check_date.weekday()} - Ist Feiertag: {check_date.strftime('%Y-%m-%d') in de_holidays}")
        # Montag bis Freitag und kein Feiertag
        if check_date.weekday() < 5 and check_date.strftime('%Y-%m-%d') not in de_holidays:
            print(f"  -> Gefunden: {check_date.strftime('%d.%m.%Y')}")
            return pd.Timestamp(check_date)

    # Fallback auf gestern
    print(f"  -> Fallback auf gestern: {yesterday.strftime('%d.%m.%Y')}")
    return pd.Timestamp(yesterday)

result = get_last_trading_day()
print(f"Ergebnis: {result.strftime('%d.%m.%Y')}")
