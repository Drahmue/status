# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
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

### Dependencies
```bash
# Install required packages
pip install -r requirements.txt
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

*Web Interface:*
5. `app.py` serves web interface that consumes both JSON data sources

**Configuration:**
- `status.ini` - Stock monitoring configuration with paths, file references, timing settings
- `status_dsl.ini` - DSL speedtest configuration with Ookla CLI path, server preferences, update intervals
- `dsl_speedtest_viewer.ini` - Viewer configuration for data analysis tools
- External dependencies on network-shared Excel files for instruments and bookings data
- Configurable refresh intervals for both stock and speedtest monitoring

**Key Data Files:**
- `prices.parquet` - Historical stock price data storage
- `speedtest_data.parquet` - Historical DSL speedtest data storage (efficient Parquet format)
- `static/depotdaten.json` - Real-time portfolio data for web interface
- `static/speedtest.json` - Current DSL speedtest data for web interface
- `status.log` - Stock monitoring application logs
- `status_dsl.log` - DSL speedtest monitoring logs
- `dsl_speedtest_viewer.log` - Data viewer application logs

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

**Web Interface & Data Management:**
- Flask-based dashboard consuming both monitoring data sources
- JSON API endpoints for real-time data
- Comprehensive error handling and logging system
- German Umlaute support throughout all components

**Deployment & Automation:**
- Windows Task Scheduler integration for automatic service startup
- Service account configuration for enterprise deployment
- Batch file automation for server deployment
- Comprehensive deployment documentation (DEPLOYMENT.md)