# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application

**Direct Python Execution (Development):**
```bash
# Start Flask web application (serves portfolio on http://localhost:5000)
python app.py

# Run stock monitoring script (fetches prices, updates data)
python status.py

# Run DSL speedtest monitoring (continuous internet speed monitoring)
python status_dsl.py

# View DSL speedtest historical data and statistics
python dsl_speedtest_viewer.py
```

**Production Deployment (PowerShell with Logging):**
```powershell
# Start Flask Web App with logging and error handling
.\start_app.ps1

# Start Stock Monitoring Service with network wait logic
.\start_status.ps1

# Start DSL Speedtest Monitoring with logging
.\start_status_dsl.ps1
```

**Task Scheduler Management:**
```powershell
# Check running tasks in AHSkripts folder
Get-ScheduledTask -TaskPath "\AHSkripts\" | Select-Object TaskName, State | Format-Table

# Start all services via Task Scheduler
Get-ScheduledTask -TaskPath "\AHSkripts\" | Start-ScheduledTask

# Stop all services via Task Scheduler
Get-ScheduledTask -TaskPath "\AHSkripts\" | Stop-ScheduledTask

# View recent logs
Get-Content "logs\app_$(Get-Date -Format 'yyyy-MM').log" -Tail 20
Get-Content "logs\status_$(Get-Date -Format 'yyyy-MM').log" -Tail 20
Get-Content "logs\status_dsl_$(Get-Date -Format 'yyyy-MM').log" -Tail 20
```

**Testing:**
```powershell
# Run automated Service-user tests (requires Administrator and password)
.\_Archiv\test_as_service_with_password.ps1
```

### Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Update virtual environment
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

## Project Architecture

This is a comprehensive monitoring system combining stock portfolio tracking with DSL speedtest monitoring, featuring Flask web visualization and efficient data storage.

  ## Coding Style Guidelines

  ### Code Organization
  - Structure code into functions rather than long procedural scripts
  - Keep main script minimal - only call main functions
  - Break complex logic into smaller, focused functions
  - Use clear function names that describe their purpose

  ### Error Handling
  - Implement comprehensive error handling for all operations
  - Use try-catch blocks around file operations, API calls, and data processing
  - Log errors with detailed context information
  - Provide meaningful error messages for debugging
  - Handle edge cases and validate inputs

  ### Variable Naming
  - Use descriptive, self-documenting variable names
  - Prefer `current_stock_price` over `price` or `p`
  - Be explicit about data types and purposes in names

  ### German Language Support
  - Support German Umlaute (ä, ö, ü, ß) in all text processing
  - Support German Umlaute (ä, ö, ü, ß) in file handling
  - Ensure proper encoding (UTF-8) for German characters
  - Handle German date formats and number formatting
  - Use German business terminology where appropriate

  ### Configuration and Logging Pattern
  - Always read an INI configuration file with the same name as the script
  - INI file should be located in the same directory as the script
  - Always include logfile name/path in the INI configuration
  - Example: `script.py` reads `script.ini` from the same directory
  - INI should contain a `[Files]` section with `logfile` parameter



### Core Components

**Main Scripts:**
- `status.py` - Core stock monitoring engine that fetches prices via yfinance, processes portfolio data, and exports JSON
- `app.py` - Flask web server that serves the monitoring dashboard
- `status_dsl.py` - DSL speedtest monitoring with continuous internet speed measurements and data storage
- `status_zaehler.py` - Gas and electricity meter monitoring via local Tasmota devices, exports JSON
- `dsl_speedtest_viewer.py` - Interactive viewer for DSL speedtest historical data and statistics
- `status_simplified.py` / `status_backup.py` - Development versions with different approaches

**Data Flow:**

*Stock Monitoring:*
1. `status.py` reads instrument definitions and booking transactions from Excel files
2. Fetches current prices using yfinance API
3. Processes portfolio positions across multiple banks/accounts
4. Exports real-time data to `static/depotdaten.json`

*DSL Speedtest Monitoring:*
1. `status_dsl.py` performs continuous internet speed measurements using Ookla CLI or Python speedtest library
2. Stores data efficiently in Parquet format (`speedtest_data.parquet`) for historical analysis
3. Exports current data to `static/speedtest.json` for web interface
4. `dsl_speedtest_viewer.py` provides interactive analysis of historical speedtest data

*Meter Monitoring (Gas & Electricity):*
1. `status_zaehler.py` queries two local Tasmota devices every 5 minutes via HTTP
2. Gas Reader (192.168.178.130): parses "Zählerstand" in m³
3. Electricity Meter / Hichi Lesekopf (192.168.178.133): parses MT691 Total Consumed, Total Delivered, Current Consumption
4. Exports current readings to `static/zaehler.json` for web interface

*Web Interface:*
5. `app.py` serves web interface that consumes all JSON data sources

**Configuration:**
- `status.ini` - Stock monitoring configuration with paths, file references, timing settings
- `status_dsl.ini` - DSL speedtest configuration with Ookla CLI path, server preferences, update intervals
- `status_zaehler.ini` - Meter monitoring configuration with Tasmota device URLs and update interval
- `dsl_speedtest_viewer.ini` - Viewer configuration for data analysis tools
- External dependencies on network-shared Excel files for instruments and bookings data
- Configurable refresh intervals for both stock and speedtest monitoring

**Key Data Files:**
- `prices.parquet` - Historical stock price data storage
- `speedtest_data.parquet` - Historical DSL speedtest data storage (efficient Parquet format)
- `static/depotdaten.json` - Real-time portfolio data for web interface
- `static/speedtest.json` - Current DSL speedtest data for web interface
- `static/zaehler.json` - Current gas and electricity meter readings for web interface

**Log Files (Centralized in `logs\` directory with monthly rotation):**
- `logs\app_YYYY-MM.log` - Flask Web App starter script logs (monthly rotation)
- `logs\status_YYYY-MM.log` - Stock Monitoring starter script logs (monthly rotation)
- `logs\status_dsl_YYYY-MM.log` - DSL Speedtest starter script logs (monthly rotation)
- `logs\status_zaehler_YYYY-MM.log` - Meter monitoring starter script logs (monthly rotation)
- `logs\*_errors_YYYY-MM.log` - Error logs for each service (created only if errors occur)
- `logs\service_test_*.log` - Automated test logs with timestamps
- Python scripts may create additional logs in root directory (configured via .ini files):
  - `status_dsl.log` - DSL monitoring Python script logs (legacy location)
  - `dsl_speedtest_viewer.log` - Data viewer application logs

**Log Management:**
- Automatic cleanup: Logs older than 120 days are deleted automatically
- Emergency fallback: If `logs\` directory is inaccessible, logs go to `C:\Temp\*_emergency_*.log`

### External Dependencies

The system depends on a shared standard library located at:
`\\WIN-H7BKO5H0RMC\Dataserver\Programmier Projekte\Python\Standardbibliothek\Standardfunktionen_aktuell.py`

This provides utility functions for logging, file operations, and configuration management.

**External Data Sources:**
- Instrument definitions: `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx`
- Transaction history: `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx`

### Key Features

**Stock Monitoring:**
- Real-time price updates with German holiday calendar integration
- Multi-bank portfolio position tracking
- Automatic data validation and forward-filling for missing prices
- Historical price data storage in Parquet format

**DSL Speedtest Monitoring:**
- Continuous internet speed monitoring with configurable intervals
- Dual speedtest support: Ookla CLI (preferred) + Python speedtest library fallback
- Efficient Parquet-based historical data storage
- Interactive data viewer with statistics and trend analysis
- Support for specific server selection (Deutsche Telekom Frankfurt)

**Meter Monitoring (Gas & Electricity):**
- Periodic polling of local Tasmota devices via HTTP (no extra library, uses stdlib urllib)
- Gas Reader at 192.168.178.130 (Smartnetz Gas Reader): Zählerstand in m³
- Electricity meter at 192.168.178.133 (Hichi Lesekopf MT691): Bezug, Einspeisung, Aktueller Verbrauch
- Exports `static/zaehler.json` every 5 minutes (configurable)

**Web Interface & Data Management:**
- Flask-based dashboard consuming both monitoring data sources
- JSON API endpoints for real-time data
- Comprehensive error handling and logging system
- German Umlaute support throughout all components

**Deployment & Automation:**
- Windows Task Scheduler integration for automatic service startup
- Service account configuration for enterprise deployment
- PowerShell-based automation for server deployment (migrated from Batch files in 2025-10-22)
- Comprehensive deployment documentation (DEPLOYMENT.md)

**PowerShell Starter Scripts:**
- `start_app.ps1` - Starts Flask Web Application with logging and error handling
- `start_status.ps1` - Starts Stock Monitoring Service with network wait logic
- `start_status_dsl.ps1` - Starts DSL Speedtest Monitoring
- `start_status_zaehler.ps1` - Starts Gas & Electricity Meter Monitoring
- All scripts include:
  - UNC path support via `Push-Location`
  - Monthly log rotation
  - Automatic log cleanup (120 days)
  - UTF-8 encoding support
  - Emergency logging fallback
  - Separate error logs

**Task Scheduler Tasks (`\AHSkripts\`):**
- `Status Web App` - Flask web application (start_app.ps1)
- `Stock Monitoring Service` - Stock monitoring (start_status.ps1), ExecutionTimeLimit=PT0S
- `DSL Speedtest Monitoring` - DSL monitoring (start_status_dsl.ps1)
- `Zaehler Monitoring` - Gas & electricity meter monitoring (start_status_zaehler.ps1)
- All tasks run under `HauServer\Service` account

**Important: Flask Template Changes**
After modifying `templates/main.html`, the Flask task must be restarted to pick up the new template (Jinja2 caches templates when not in debug mode):
```powershell
Stop-ScheduledTask -TaskName "Status Web App" -TaskPath "\AHSkripts\"
Start-ScheduledTask -TaskName "Status Web App" -TaskPath "\AHSkripts\"
```

**Testing & Deployment Tools:**
- `_Archiv\test_as_service_with_password.ps1` - Automated Service-user testing with password authentication
- `_Archiv\update_production_tasks.ps1` - Updates Task Scheduler tasks from Batch to PowerShell
- `_Archiv\move_tasks_to_ahskripts.ps1` - Relocates tasks to correct Task Scheduler folder

## Documentation

### Project Documentation Files

- **CLAUDE.md** - This file: Development guidelines and project architecture overview
- **DEPLOYMENT.md** - Comprehensive Windows Server deployment guide (Version 2.0, PowerShell-based)
- **README.md** - Project overview and quick start guide
- **CHANGELOG_2025-10-22.md** - PowerShell migration, centralized logging, testing, and deployment
- **CHANGELOG_2025-10-20.md** - UNC path problem resolution and initial PowerShell conversion
- **CHANGELOG_2025-10-17.md** - Network wait logic implementation for reliable startup

### Key Documentation Updates (2025-10-22)

The system underwent a major upgrade from Batch to PowerShell:
1. **Migration to PowerShell** - All starter scripts converted from .bat to .ps1
2. **Centralized Logging** - New `logs\` directory with monthly rotation
3. **Automated Testing** - PowerShell test framework with Service account authentication
4. **Task Scheduler Updates** - All tasks updated to use PowerShell with proper credentials
5. **Comprehensive Documentation** - DEPLOYMENT.md rewritten to Version 2.0

See CHANGELOG_2025-10-22.md for detailed migration documentation.

## Known Issues and Fixes

### Reference Date Update Bug (Fixed: 2025-10-22)

**Problem:**
The stock monitoring service displayed an outdated reference date (last trading day) even though the actual last trading day had changed. For example, showing "17.10.2025" when the current last trading day should be "21.10.2025".

**Root Cause:**
In the `run_monitor()` function in `status.py` (lines 405-420), the logic for updating the reference date had a critical flaw:

1. When a new trading day was detected, `current_last_trading_day` was immediately updated to the new date
2. Then the script checked if shares data was available for that date
3. If no shares data existed, `current_shares_yesterday` was set to `None`
4. However, `current_last_trading_day` remained set to the new date
5. This caused `get_reference_values_from_yfinance()` to be called with `None` for shares data
6. Result: Empty reference data and outdated/frozen reference date in output

**Symptoms:**
- Reference date in `static/depotdaten.json` not updating to current last trading day
- Warning message: "Keine Daten für {date} verfügbar. Verwende alte Daten."
- Portfolio calculations based on outdated reference date

**Fix Implemented:**
Modified the update logic in `status.py` to only update reference values when shares data is available:

```python
if new_last_trading_day != current_last_trading_day:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Neuer Handelstag erkannt: {new_last_trading_day.strftime('%d.%m.%Y')}")

    # Prüfe, ob Shares-Daten für den neuen Handelstag verfügbar sind
    new_shares_yesterday = shares_day_df.loc[new_last_trading_day] if new_last_trading_day in shares_day_df.index else None

    if new_shares_yesterday is None:
        screen_and_log(f"WARNING: Keine Shares-Daten für neuen Handelstag {new_last_trading_day.strftime('%d.%m.%Y')} verfügbar", logfile)
        print(f"Warnung: Keine Daten für {new_last_trading_day.strftime('%d.%m.%Y')} verfügbar. Behalte altes Referenzdatum {current_last_trading_day.strftime('%d.%m.%Y')} bei.")
        # WICHTIG: Behalte die alten Werte bei - NICHT aktualisieren!
    else:
        # Nur aktualisieren, wenn Daten verfügbar sind
        current_last_trading_day = new_last_trading_day
        current_shares_yesterday = new_shares_yesterday
        screen_and_log(f"Info: Referenzdaten für neuen Handelstag {current_last_trading_day.strftime('%d.%m.%Y')} aktualisiert", logfile)
        print(f"Info: Referenzdatum aktualisiert auf {current_last_trading_day.strftime('%d.%m.%Y')}")
```

**Key Changes:**
1. Check for shares data availability **before** updating `current_last_trading_day`
2. Only update both `current_last_trading_day` and `current_shares_yesterday` together if data is available
3. If no data available, keep the old values and log a warning
4. Ensures reference date and shares data remain synchronized

**Verification:**
After restarting the Stock Monitoring Service, the reference date correctly updates to the current last trading day. The fix ensures data consistency and prevents calculation errors.

**Related Files:**
- `status.py` (lines 405-420) - Main fix location
- `static/depotdaten.json` - Output file with reference_date field

### Task Scheduler ExecutionTimeLimit Bug (Fixed: 2026-02-27)

**Problem:**
The Stock Monitoring Service stopped after exactly ~72 hours without any log entry. Exit code 267014 was recorded by Task Scheduler.

**Root Cause:**
Task Scheduler's default `ExecutionTimeLimit` is `PT72H` (72 hours) when `UseUnifiedSchedulingEngine=true` and no explicit limit is configured. After 72 hours, Windows forcibly terminates the process – no warning, no log entry.

**Symptoms:**
- Service state changes from `Running` to `Ready` after ~72 hours
- Last JSON update timestamp is exactly ~72h after last task start time
- Exit code 267014 in Task Scheduler
- No error entries in Python log (`status.log`)

**Fix Implemented:**
Set `ExecutionTimeLimit = PT0S` (no limit) on the Stock Monitoring Service task:

```powershell
$task = Get-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\"
$task.Settings.ExecutionTimeLimit = "PT0S"
Set-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" `
    -Settings $task.Settings -User "WIN-H7BKO5H0RMC\Service" -Password $pw
```

**Related Files:**
- Task Scheduler: `\AHSkripts\Stock Monitoring Service`
- `TROUBLESHOOTING_STOCK_MONITORING.md` - Detailed diagnosis steps

### Silent Crash in run_monitor() (Fixed: 2026-02-27)

**Problem:**
The `while True` loop in `run_monitor()` had no outer `try/except` block. Any unhandled exception (e.g. yfinance network error, API timeout) would silently terminate the entire Python process with no log entry.

**Root Cause:**
Several calls outside the per-WKN `try/except` block could raise unhandled exceptions:
- `get_last_trading_day()`, `get_current_prices()`, `get_reference_values_from_yfinance()`
- `pd.DataFrame(output_rows)`, `open("static/depotdaten.json", 'w', ...)`

**Fix Implemented:**
Added outer `try/except` in `run_monitor()` in `status.py`:
- Full traceback logged to `status.log` on exception
- Loop continues after `refresh_time` seconds instead of crashing
- `refresh_time` moved before the `try` block so it is available in `except`
- `import traceback` added at top of file

**Related Files:**
- `status.py` (`run_monitor()` function) - Main fix location
- `status.log` - Will now contain ERROR entries with full traceback on failures

### NTFS Permission Bug After Server Rebuild (Fixed: 2026-07-15)

**Problem:**
After rebuilding the Windows Server (WS2022 → WS2025) and recreating all Task Scheduler tasks, `status.py` failed under the `Service` account with:
```
RuntimeError: [Errno 13] Permission denied: '\\HauServer\Dataserver\Dummy\Finance_Input\Instrumente.xlsx'
```
Manual execution as Administrator worked fine; only the Service-account/Task-Scheduler context failed.

**Root Cause:**
`is_file_open_windows()` in `ahlib.py` (`.venv\Lib\site-packages\ahlib\ahlib.py`, called from `files_availability_check()`) opens the target file in write mode (`open(file_path, 'r+b')`) to test for a lock via `msvcrt.locking()` — even though it never writes. This requires NTFS **Modify** rights, not just Read & Execute. After the server rebuild, the `Service` account's NTFS ACL on `Finance_Input` had only been (re-)granted `(RX)` instead of `(M)`, so the lock-check itself failed with Permission Denied even though the file was fully readable and visible (`Test-Path` returned `True`).

**Not the cause (ruled out during diagnosis):** `DisableLoopbackCheck` / `BackConnectionHostNames` are IIS/HTTP-only NTLM-loopback settings and have no effect on SMB file access. SMB share-level permissions (`Get-SmbShareAccess`) were already correct (`Change` for `Service`) — the NTFS ACL was the sole bottleneck.

**Fix Implemented:**
```powershell
icacls "D:\Dataserver\Dummy\Finance_Input" /grant "HAUSERVER\Service:(OI)(CI)M" /T
```
Grants Modify recursively, additive to existing ACEs.

**Related Files:**
- `.venv\Lib\site-packages\ahlib\ahlib.py` (`is_file_open_windows()`, line ~498) - Root cause location
- `DEPLOYMENT.md` §2.1 - Already specified Modify as minimum; ensure this is actually applied after any server/account rebuild
- `TROUBLESHOOTING_STOCK_MONITORING.md` - Detailed diagnosis steps and verification commands
- `CHANGELOG_2026-07-15.md` - Full incident writeup