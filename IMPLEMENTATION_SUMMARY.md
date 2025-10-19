# Earnings Events Tracker - Implementation Summary

## Overview
A solution for tracking upcoming earnings reports for portfolio stocks using the Alpha Vantage API. Events are filtered to the next 2 months, sorted chronologically, and presented to the user in a clean format.

## Files Created

### 1. `agent/events_tracker.py` (Main Module)
Core module handling all event tracking logic:
- **`load_alpha_vantage_api_key()`** - Retrieves API key from macOS Keychain
- **`load_ticker_mapping()`** - Loads stock name to ticker symbol mappings
- **`get_ticker_for_asset()`** - Maps portfolio asset names to ticker symbols with error handling
- **`fetch_earnings_calendar()`** - Calls Alpha Vantage EARNINGS_CALENDAR endpoint
- **`parse_date()`** - Handles multiple date formats from API responses
- **`filter_upcoming_events()`** - Filters events to 60-day window (2 months)
- **`sort_events_chronologically()`** - Sorts all events by date (earliest first)
- **`get_portfolio_upcoming_events()`** - Main orchestration function that:
  - Validates all stocks are mapped
  - Fetches earnings reports
  - Filters and sorts events
  - Returns structured result with error handling

### 2. `ticker_mapping.json` (Configuration)
Template file for stock name to ticker symbol mappings:
- Pre-populated with example mappings
- Instructions for European stock suffixes (.L, .PA, etc.)
- Clear notes about exact name matching requirements
- User fills in actual mappings for their portfolio

### 3. `setup_alpha_vantage.sh` (Setup Script)
Bash script to securely store Alpha Vantage API key in macOS Keychain:
- Prompts user for API key input (hidden)
- Stores in keychain under "mcp-portfolio-agent" service
- Handles key updates gracefully
- Provides clear success/failure feedback

### 4. `agent/main.py` (MCP Tool Addition)
Added new tool `get_upcoming_events()`:
- Retrieves normalized portfolio data from Google Sheets
- Calls events_tracker to get upcoming events
- Formats results beautifully with:
  - Event type (Earnings Report)
  - Ticker symbol & company name
  - Event date & days until event
  - Additional info (earnings estimate)
  - Summary statistics
- Provides helpful error messages for:
  - Missing API key
  - Unmapped stocks with specific names
  - Network/API failures

### 5. `AGENTS.md` (Documentation Updates)
Enhanced documentation with:
- Alpha Vantage setup instructions
- Ticker mapping configuration guide
- Available tools documentation
- Important notes about event filtering and stock format

## Key Features

### ✅ Event Filtering (2-Month Window)
- Only shows events within 60 days from today
- Configurable via `DAYS_THRESHOLD` constant in events_tracker.py
- Prevents overwhelming users with distant future events

### ✅ Chronological Sorting
- All earnings events sorted by date (earliest first)
- Easy to see upcoming earnings announcements

### ✅ Error Handling
Three-tier error handling:
1. **API Key Error**: Clear message with setup instructions
2. **Unmapped Stock Error**: Lists all unmapped stocks with action items
3. **Network Error**: Graceful handling of API failures

### ✅ Ticker Mapping System
- Centralized JSON file for all stock mappings
- Clear distinction between US and European stocks
- User-maintained for flexibility
- Validates all portfolio stocks before API calls

### ✅ Secure Credential Storage
- API key stored in macOS Keychain (never in files)
- Uses same pattern as existing Google Sheets credentials
- Setup script provided for easy configuration

### ✅ Excluded Asset Types
- Cash positions automatically excluded
- Pension funds excluded
- Only stocks/ETFs tracked

## Data Model

### Event Structure (Output)
```python
{
    "type": "Earnings Report",
    "ticker": "AAPL",
    "company_name": "Apple Inc",
    "date": "2025-11-15",
    "days_until": 27,
    "report_date": "2025-11-15",
    "estimate": "1.25"
}
```

### Error Response Structure
```python
{
    "success": False,
    "error": "Unmapped stocks found",
    "unmapped_stocks": ["Stock Name 1", "Stock Name 2"],
    "action": "Please update ticker_mapping.json..."
}
```

## API Endpoints Used

**Alpha Vantage - EARNINGS_CALENDAR**
- Fetches upcoming earnings report dates
- Includes earnings estimates
- Returns: `reportDate`, `symbol`, `estimate`

## Setup Instructions

### 1. Store API Key
```bash
./setup_alpha_vantage.sh
# Enter your Alpha Vantage API key when prompted
```

### 2. Configure Ticker Mappings
Edit `ticker_mapping.json`:
```json
{
  "mappings": {
    "Apple Inc": "AAPL",
    "Microsoft Corporation": "MSFT",
    "ASML Holding": "ASML",
    "Wise": "WISE.L"
  }
}
```

### 3. Run Tool
```
get_upcoming_events()
```

## Important Notes

- **Rate Limiting**: Alpha Vantage has rate limits (5 calls/min for free tier). Single API call per invocation.
- **Stock Coverage**: Not all stocks are available on Alpha Vantage. European stocks need proper exchange suffix.
- **Data Freshness**: Alpha Vantage updates earnings calendar data periodically (not real-time).
- **Timezone**: All dates are handled in UTC internally.
- **API Calls**: 1 per invocation (earnings only)

## Future Enhancements

Potential improvements:
- Caching to reduce API calls
- Batch processing for large portfolios
- Customizable event filters (by company, event type, etc.)
- Alert notifications for events
- Historical event tracking
- Multiple API provider support

## Testing

To verify the implementation:
1. Ensure Python syntax: `python3 -m py_compile agent/events_tracker.py agent/main.py`
2. Verify JSON config: `python3 -c "import json; json.load(open('ticker_mapping.json'))"`
3. Check setup script: `bash setup_alpha_vantage.sh --help` (if added)

All files follow project code style guidelines:
- Python 3.12+ compatible
- Type hints on all functions
- Google-style docstrings
- 4-space indentation
- Error logging with context
