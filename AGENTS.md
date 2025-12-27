# AGENTS.md - Development Guidelines

## Build/Test Commands
- **Install dependencies**: `uv sync`
- **Run server**: `uv run python server.py`
- **Run all config tests**: `uv run python test_config.py`
- **Run all GCP storage tests**: `uv run python test_gcp_storage.py`
- **Run dashboard tests**: `uv run python test_dashboard.py`
- **Run single test file**: `uv run python test_<name>.py`
- **Check setup**: `uv run python check_setup.py`
- **Package management**: Use `uv` for all dependency management (NOT pip)

## Code Style Guidelines

### Imports
- **Order**: Standard library, blank line, third-party, blank line, local imports
- **From imports**: Use `from typing import Dict, List, Optional, Any` for type hints
- **Module imports**: Use `import logging`, `import json`, etc. for standard library
- **Relative imports**: Use `from . import config` and `from .config_models import InvestmentConfig`
- **Example**:
```python
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from . import config
from .config_models import InvestmentConfig
```

### Formatting & Style
- **Python version**: 3.12+ (as specified in pyproject.toml)
- **Strings**: Always use double quotes (`"string"` not `'string'`)
- **Indentation**: 4 spaces (no tabs)
- **Line length**: ~100 characters max (flexible, prioritize readability)
- **Trailing commas**: Use in multi-line lists, dicts, and function arguments

### Type Hints
- **Required**: All function signatures must have type hints
- **Parameters**: Type hint all parameters
- **Returns**: Always specify return type (use `None` if no return value)
- **Example**:
```python
def get_ticker_for_stock(stock_name: str) -> Optional[str]:
    """Get ticker symbol for a stock name."""
    return get_config().ticker_mappings.get(stock_name)
```

### Docstrings
- **Style**: Google-style docstrings for all public functions and classes
- **Format**: Triple double-quotes, summary line, blank line, details
- **Include**: Args, Returns, Raises sections as applicable
- **Example**:
```python
def save_snapshot(snapshot_data: Dict[str, Any]) -> None:
    """
    Save a portfolio snapshot to storage.
    
    Validates snapshot structure and saves to configured backend
    (GCP primary with local fallback).
    
    Args:
        snapshot_data: Dictionary conforming to Snapshot JSON Schema
        
    Raises:
        ValueError: If snapshot data is invalid
        IOError: If all storage backends fail
    """
```

### Naming Conventions
- **Functions/variables**: `snake_case` (e.g., `get_latest_snapshot`, `total_value_eur`)
- **Classes**: `PascalCase` (e.g., `InvestmentConfig`, `GCPStorageBackend`)
- **Constants**: `UPPER_SNAKE_CASE` at module level (e.g., `CACHE_DIR`, `API_RATE_LIMIT_DELAY`)
- **Private functions**: Prefix with `_` (e.g., `_get_storage_backend`, `_validate_snapshot_structure`)
- **Module-level globals**: Prefix with `_` and type hint (e.g., `_config: Optional[InvestmentConfig] = None`)

### Error Handling
- **Specific exceptions**: Always catch specific exception types, never bare `except:`
- **Context**: Log errors with context using `logger.error()`
- **Re-raise**: Re-raise with enhanced error messages when appropriate
- **Example**:
```python
try:
    config = InvestmentConfig(**yaml_data)
except ValidationError as e:
    raise ValueError(
        f"❌ CRITICAL: Configuration validation failed.\n\n"
        f"Errors in {config_path}:\n{e}\n\n"
        f"Please fix the configuration errors above."
    )
```

### Logging
- **Setup**: Use module-level logger: `logger = logging.getLogger(__name__)`
- **Levels**: INFO for operations, WARNING for recoverable issues, ERROR for failures
- **Messages**: Clear, actionable messages with context
- **Example**: `logger.info(f"Retrieved {len(snapshots)} snapshots from storage")`

### File Organization
- **Module structure**: Related functions grouped in focused modules
- **Core modules**: `agent/` directory (config.py, storage.py, sheets_connector.py, analysis.py, etc.)
- **Backends**: `agent/backends/` for pluggable storage implementations
- **Providers**: `agent/providers/` for external data source integrations
- **Tests**: Root directory, named `test_<module>.py`

### Comments & Documentation
- **Focus on why**: Comments explain why, not what (code should be self-documenting)
- **Inline comments**: Avoid unless necessary for complex logic
- **Module docstrings**: Every module has a docstring explaining its purpose
- **TODO comments**: Use `# TODO:` for future improvements (rare, prefer issues)

### Configuration & Credentials
- **Never hardcode**: No hardcoded credentials, API keys, or sensitive data in code
- **Keychain**: Store all credentials in macOS Keychain
- **Config file**: Use `config.yaml` for all configurable values
- **Env vars**: Support environment variable overrides for testing/CI

## Project Structure
- `agent/` - Core modules (config.py, storage.py, sheets_connector.py, analysis.py, reporting.py, events_tracker.py, risk_analysis.py, insider_trading.py, short_volume.py, visualization.py)
- `agent/backends/` - Storage backend implementations (gcp_storage.py, local_storage.py, hybrid_storage.py)
- `agent/providers/` - Data provider implementations (yahoo_earnings_provider.py)
- `agent/config_models.py` - Pydantic v2 configuration schema models
- `agent/earnings_models.py` - Generic earnings data models
- `agent/earnings_provider.py` - Abstract earnings provider interface
- `agent/visualization.py` - Interactive HTML dashboard generation with Plotly
- `server.py` - FastMCP server entry point
- `config.yaml` - Main configuration file (REQUIRED)
- `config.yaml.example` - Template with documentation
- `pyproject.toml` - Project metadata and dependencies
- `dashboards/` - Generated HTML dashboards (auto-created, gitignored)
- `cache/` - Cached historical price data (auto-created)
- `test_*.py` - Test files (root directory)
- Credentials stored securely in macOS Keychain, never in files

## API Setup

### Alpha Vantage API (Risk Analysis Only)

**Note:** Alpha Vantage is now only used for risk analysis (historical price data). Earnings dates are fetched from Yahoo Finance (no API key required).

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
Edit `config.yaml` and add mappings for all stocks in your portfolio:
```yaml
ticker_mappings:
  Apple Inc: AAPL
  Microsoft Corporation: MSFT
  ASML Holding: ASML
  Wise: WISE.L
```

### 3. Available MCP Tools

#### Portfolio Analysis & Tracking
- `run_portfolio_analysis()` - Triggers full portfolio analysis and generates weekly performance report
- `get_portfolio_status()` - Returns current portfolio total value, asset count, and last update timestamp
- `get_portfolio_history_summary()` - Shows portfolio performance since first snapshot
- `get_latest_positions()` - Displays all current positions organized by category (Stocks, Bonds, ETFs, Pension, Cash) with gain/loss details

#### Events & Earnings Tracking
- `get_upcoming_events()` - Fetches upcoming earnings reports for portfolio stocks within the next 2 months, sorted chronologically:
  - Data from Yahoo Finance (free, no API key required)
  - Automatically excludes bonds, ETFs, pension, and cash positions
  - Uses ticker_mappings from config.yaml to resolve stock tickers
  
- `get_earnings_date(ticker)` - Get next earnings date for a specific stock ticker:
  - Supports any ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
  - Returns report date, company name, days until, and earnings estimate
  - Data from Yahoo Finance (free, no API key required)

#### Risk Analysis
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
  - Uses ticker_mappings from config.yaml to resolve stock tickers
  
  **Note:** All outputs include "Data provided by Fintel.io" attribution as required by Fintel's terms

#### Short Volume Tracking
- `get_short_volume(ticker, days=30)` - Fetches short selling activity for a specific stock over specified period:
  - Daily short volume and total volume data
  - Short volume ratio (percentage of daily volume that's short)
  - 7-day and 30-day average short ratios
  - Trend analysis (Increasing/Decreasing/Stable)
  - Risk assessment based on short selling patterns
  - Data from Fintel.io `/ss/` endpoint
  
- `get_portfolio_short_analysis()` - Analyzes short selling activity across all portfolio stocks:
  - Stocks organized by risk level (High/Medium/Low)
  - Average short ratio per stock with trend indicators
  - Risk scoring based on short volume patterns
  - Automatically excludes bonds, ETFs, pension, and cash positions
  - Uses ticker_mappings from config.yaml to resolve stock tickers
  
  **Note:** Short interest data (% of float, days to cover) not available in current Fintel API tier

#### Portfolio Visualization
- `generate_portfolio_dashboard(time_period="all")` - Generate interactive HTML dashboard with Plotly charts:
  - **Time periods**: "7d", "30d", "90d", "1y", "all" (default: "all")
  - **Auto-generated**: After each `run_portfolio_analysis()` call
  - **Output**: `dashboards/portfolio_dashboard.html` (overwritten each time)
  - **Charts included**:
    - Portfolio Value vs Benchmarks (SPY, VT) - Line chart comparing portfolio growth against S&P 500 and All-World Index
    - Category Allocation Over Time - Stacked area chart showing evolution of asset categories
    - Individual Asset Performance - Multi-line chart with top 10 assets shown by default, all selectable via legend
    - Top Holdings Evolution - Area chart tracking your largest positions over time
    - Gain/Loss Analysis - Horizontal bar chart showing profit/loss for current positions
    - Transaction Timeline - Scatter plot with markers showing buy/sell activity
    - Currency Exposure Breakdown - Stacked area chart of USD/EUR/GBP exposure
    - Risk Metrics Dashboard - 2x2 grid showing cumulative returns, max drawdown, rolling volatility, and value distribution
  - **Interactive features**:
    - Time period selector dropdown (client-side filtering)
    - Multi-select assets via legend clicks
    - Zoom, pan, hover tooltips on all charts
    - Toggle series visibility on/off
  - **Benchmarks**: S&P 500 (SPY) and All-World Index (VT) normalized to portfolio start value, fetched from Yahoo Finance
  - **Requirements**: At least 2 snapshots in portfolio history
  - **Note**: Dashboard generation may take 10-30 seconds due to benchmark data fetching

### Notes
- **Earnings Tracking:**
  - Earnings reports are filtered to show only those within 60 days (2 months)
  - Data is fetched from Yahoo Finance (free, no API key required)
  - Provider architecture allows easy switching to other data sources in the future
  - All earnings data includes source attribution
  
- **Risk Analysis:**
  - Historical price data is cached for 24 hours in the `cache/` directory to minimize API calls
  - Risk analysis uses 252 trading days (1 year) of historical data for calculations
  - Risk analysis may take several minutes due to API rate limits (12s delay between calls)
  - Uses Alpha Vantage API (requires API key)
  
- **Insider Trading:**
  - Data is filtered to last 90 days
  - Sentiment is based on 2:1 buy/sell value ratio (>2x buys = Bullish, >2x sells = Bearish)
  - Option exercises with null values are counted as buys but excluded from value calculations
  - All insider trading outputs must include Fintel.io attribution
  
- **Short Volume:**
  - Shows daily short selling activity (typically 10+ days of historical data)
  - Short volume ratio = (short volume / total volume) × 100
  - Trend analysis compares recent 7-day avg vs previous 7-day avg (±10% threshold)
  - Risk scoring: High (>40% ratio or score ≥5), Medium (30-40% or score 3-4), Low (<30% or score <3)
  - All short volume outputs must include Fintel.io attribution
  
- **Portfolio Visualization:**
  - Dashboard requires at least 2 snapshots in portfolio history
  - Benchmark data (SPY, VT) fetched from Yahoo Finance using yfinance library
  - Time period filtering happens client-side via dropdown selector
  - Dashboard file size typically 100-200KB depending on data volume
  - All timestamps normalized to UTC to ensure proper alignment with benchmark data
  - Requires internet connection for initial generation (benchmark fetching)
  - Dashboard is fully standalone HTML with embedded Plotly.js (no external dependencies once generated)
  
- **General:**
  - Missing ticker mappings will trigger an error with clear instructions to update `config.yaml`
  - For European stocks, include the exchange suffix in ticker_mappings (e.g., `.L` for London, `.PA` for Paris, `.AS` for Amsterdam)
  - Cash, bonds, and pension positions are automatically excluded from event tracking, risk analysis, insider trading, and short volume