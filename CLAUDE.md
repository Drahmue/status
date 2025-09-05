# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
# Start Flask web application (serves portfolio on http://localhost:5000)
python app.py

# Run stock monitoring script (fetches prices, updates data)
python status.py
```

### Dependencies
```bash
# Install required packages
pip install -r requirements.txt
```

## Project Architecture

This is a Flask-based stock portfolio monitoring system that combines real-time price fetching with web visualization.

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
- `app.py` - Simple Flask web server that serves the portfolio dashboard
- `status_simplified.py` / `status_backup.py` - Development versions with different approaches

**Data Flow:**
1. `status.py` reads instrument definitions and booking transactions from Excel files
2. Fetches current prices using yfinance API
3. Processes portfolio positions across multiple banks/accounts
4. Exports real-time data to `static/depotdaten.json`
5. `app.py` serves web interface that consumes the JSON data

**Configuration:**
- `status.ini` - Main configuration file with paths, file references, timing settings
- External dependencies on network-shared Excel files for instruments and bookings data
- Configurable refresh intervals for price updates

**Key Data Files:**
- `prices.parquet` - Historical price data storage
- `static/depotdaten.json` - Real-time portfolio data for web interface
- `status.log` - Application logs with comprehensive error tracking

### External Dependencies

The system depends on a shared standard library located at:
`\\WIN-H7BKO5H0RMC\Dataserver\Programmier Projekte\Python\Standardbibliothek\Standardfunktionen_aktuell.py`

This provides utility functions for logging, file operations, and configuration management.

**External Data Sources:**
- Instrument definitions: `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx`
- Transaction history: `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx`

### Key Features

- Real-time price updates with German holiday calendar integration
- Multi-bank portfolio position tracking
- Automatic data validation and forward-filling for missing prices
- Web-based dashboard with JSON API endpoint
- Comprehensive error handling and logging system