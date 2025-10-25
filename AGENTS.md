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
- `agent/` - Core modules (main.py, analysis.py, sheets_connector.py, storage.py, reporting.py, events_tracker.py, risk_analysis.py, insider_trading.py)
- `server.py` - FastMCP server entry point
- `pyproject.toml` - Project configuration with dependencies
- `ticker_mapping.json` - Mapping of portfolio stock names to ticker symbols
- `cache/` - Cached historical price data from Alpha Vantage (auto-created)
- Credentials stored securely in macOS Keychain, never in files

## API Setup

### Alpha Vantage API (Events & Risk Analysis)

#### 1. Store API Key in Keychain
```bash
./setup_alpha_vantage.sh
```
Or manually:
```bash
security add-generic-password -a "mcp-portfolio-agent" -s "alpha-vantage-api-key" -w "YOUR_API_KEY_HERE" -U
```

### Fintel API (Insider Trading)

#### 1. Store API Key in Keychain
```bash
./setup_fintel.sh
```
Or manually:
```bash
security add-generic-password -a "mcp-portfolio-agent" -s "fintel-api-key" -w "YOUR_API_KEY_HERE" -U
```

### Ticker Mappings
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

### 3. Available MCP Tools

#### Portfolio Analysis & Tracking
- `run_portfolio_analysis()` - Triggers full portfolio analysis and generates weekly performance report
- `get_portfolio_status()` - Returns current portfolio total value, asset count, and last update timestamp
- `get_portfolio_history_summary()` - Shows portfolio performance since first snapshot
- `get_latest_positions()` - Displays all current positions organized by category (Stocks, Bonds, ETFs, Pension, Cash) with gain/loss details

#### Events & Risk Analysis
- `get_upcoming_events()` - Fetches upcoming earnings reports for portfolio stocks within the next 2 months, sorted chronologically
- `analyze_portfolio_risk()` - Performs comprehensive risk analysis including:
  - Portfolio beta (market sensitivity vs S&P 500)
  - Value at Risk (VaR) at 95% and 99% confidence levels
  - Concentration risk score (HHI index)
  - Correlation matrix between holdings
  - Sector/geography exposure breakdown
  - Volatility by asset class
  - Downside risk metrics (Sortino ratio, max drawdown, CVaR)
  
  **Note:** Risk analysis fetches historical price data from Alpha Vantage and may take several minutes due to API rate limits (12s delay between calls)

#### Insider Trading
- `get_insider_trades(ticker)` - Fetches insider trading data for a specific stock ticker over the last 90 days:
  - Buy/sell transaction counts and values
  - Net sentiment (Bullish/Neutral/Bearish based on 2:1 buy/sell ratio)
  - Recent transaction details (insider name, date, type, shares, value)
  - Data from Fintel.io Web Data API
  
- `get_portfolio_insider_trades()` - Analyzes insider trading for all portfolio stocks:
  - Stocks organized by sentiment (Bullish/Neutral/Bearish)
  - Summary statistics per stock
  - Automatically excludes bonds, ETFs, pension, and cash positions
  - Uses ticker_mapping.json to resolve stock tickers
  
  **Note:** All outputs include "Data provided by Fintel.io" attribution as required by Fintel's terms

### Notes
- **Earnings & Risk Analysis:**
  - Earnings reports are filtered to show only those within 60 days (2 months)
  - Only EARNINGS_CALENDAR endpoint is used (dividend data not available from Alpha Vantage)
  - Historical price data is cached for 24 hours in the `cache/` directory to minimize API calls
  - Risk analysis uses 252 trading days (1 year) of historical data for calculations
  - Risk analysis may take several minutes due to API rate limits (12s delay between calls)
  
- **Insider Trading:**
  - Data is filtered to last 90 days
  - Sentiment is based on 2:1 buy/sell value ratio (>2x buys = Bullish, >2x sells = Bearish)
  - Option exercises with null values are counted as buys but excluded from value calculations
  - All insider trading outputs must include Fintel.io attribution
  
- **General:**
  - Missing ticker mappings will trigger an error with clear instructions to update `ticker_mapping.json`
  - For European stocks, include the exchange suffix (e.g., `.L` for London, `.PA` for Paris, `.AS` for Amsterdam)
  - Cash, bonds, and pension positions are automatically excluded from event tracking, risk analysis, and insider trading