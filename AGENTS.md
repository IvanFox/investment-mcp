# AGENTS.md - Development Guidelines

## Build/Test Commands
- **Install dependencies**: `uv sync`
- **Run server**: `python server.py`
- **Run single test**: No test framework configured (add pytest for testing)
- **Check setup**: `python check_setup.py`
- **Package management**: Use `uv` for all dependency management

## Code Style Guidelines
- **Python version**: 3.12+ (as specified in pyproject.toml)
- **Imports**: Standard library first, third-party, then local imports with blank lines between groups
- **Formatting**: Use double quotes for strings, 4-space indentation
- **Type hints**: Required for function signatures, use `typing` module imports
- **Docstrings**: Google-style docstrings for all functions and classes
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Constants**: UPPER_CASE constants at module level
- **Error handling**: Use try/except blocks with specific exception types, log errors with context
- **Logging**: Use module-level logger = logging.getLogger(__name__)
- **File organization**: Related functions in modules (sheets_connector, analysis, storage, reporting)
- **Comments**: Focus on why not what, avoid inline comments unless necessary
- **Line length**: Keep reasonable (appears to follow ~100 char limit from examples)
- **Returns**: Always specify return types and document return values in docstrings

## Project Structure
- `agent/` - Core modules (main.py, analysis.py, sheets_connector.py, storage.py, reporting.py, events_tracker.py)
- `server.py` - FastMCP server entry point
- `pyproject.toml` - Project configuration with dependencies
- `ticker_mapping.json` - Mapping of portfolio stock names to ticker symbols
- Credentials stored securely in macOS Keychain, never in files

## Alpha Vantage API Setup

### 1. Store API Key in Keychain
```bash
./setup_alpha_vantage.sh
```
Or manually:
```bash
security add-generic-password -a "mcp-portfolio-agent" -s "alpha-vantage-api-key" -w "YOUR_API_KEY_HERE" -U
```

### 2. Configure Ticker Mappings
Edit `ticker_mapping.json` and add mappings for all stocks in your portfolio:
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

### 3. Available Tools
- `get_upcoming_events()` - Fetches upcoming earnings reports for portfolio stocks within the next 2 months, sorted chronologically

### Notes
- Earnings reports are filtered to show only those within 60 days (2 months)
- Only EARNINGS_CALENDAR endpoint is used (dividend data not available from Alpha Vantage)
- Missing ticker mappings will trigger an error with clear instructions to update `ticker_mapping.json`
- For European stocks, include the exchange suffix (e.g., `.L` for London, `.PA` for Paris)
- Cash, bonds, and pension positions are automatically excluded from event tracking