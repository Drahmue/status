# Stock Monitor Web Application

A Flask-based web application for monitoring stock portfolio performance with real-time price updates and historical data tracking.

## Features

- **Real-time Stock Monitoring**: Fetches current stock prices using Yahoo Finance API
- **Portfolio Tracking**: Tracks stock positions across multiple banks/accounts
- **Historical Data**: Maintains price history with automatic updates
- **Web Interface**: Simple HTML interface for viewing portfolio status
- **JSON API**: Exposes portfolio data via JSON endpoint

## Project Structure

```
├── app.py                          # Flask web application
├── status.py                       # Main stock monitoring script
├── status.ini                      # Configuration settings
├── prices.parquet                  # Historical price data
├── status.log                      # Application logs
├── static/
│   ├── depotdaten.json            # Real-time portfolio data
│   ├── speedtest.json             # Network performance data
│   └── style.css                  # Styling for web interface
└── templates/
    ├── main.html                  # Current web template
    └── [other template versions]   # Historical template versions
```

## Installation

1. Install required Python packages:
```bash
pip install flask pandas yfinance numpy openpyxl holidays
```

2. Configure settings in `kursabfrage_settings.ini`

3. Set up your instrument and booking data files as specified in settings

## Usage

### Web Interface
```bash
python app.py
```
Access the web interface at `http://localhost:5000`

### Stock Monitor
```bash
python status.py
```

## Configuration

Edit `status.ini` to configure:
- File paths for instruments, bookings, and price data
- Logging settings
- Output preferences

## Data Files

- **Instruments**: Excel file containing stock symbols, names, and default values
- **Bookings**: Excel file with transaction history (date, stock, bank, quantity)
- **Prices**: Parquet file with historical price data

## Features Detail

### Stock Data Processing
- Automatic price updates for missing trading days
- Forward-fill for missing price data
- Multi-bank portfolio tracking
- German holiday calendar integration

### Real-time Monitoring
- Fetches current prices every 10 seconds
- Calculates price differences and percentage changes
- Tracks total portfolio value changes
- Exports data to JSON for web interface

### Error Handling
- Comprehensive logging system
- Data validation and consistency checks
- Graceful handling of missing data or API failures

## License

This project is for personal use in stock portfolio monitoring and analysis.