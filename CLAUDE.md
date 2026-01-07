# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment MCP Agent - An automated portfolio monitoring and performance analysis system built with FastMCP. Tracks complete investment portfolios (stocks, bonds, ETFs, pension, cash) across multiple currencies with interactive dashboards, risk analysis, insider trading monitoring, and comprehensive reporting.

## Common Commands

### Development Setup
```bash
uv sync                              # Install all dependencies
python check_setup.py                # Verify configuration and credentials
```

### Running the Application
```bash
uv run python server.py              # Start the FastMCP server
uv run python -m agent.main          # Run portfolio analysis directly
uv run python run_events.py          # Get upcoming earnings events
```

### Testing
```bash
uv run python test_config.py         # Test configuration loading
uv run python test_gcp_storage.py    # Test GCP storage backend
uv run python test_dashboard.py      # Test dashboard generation
uv run python test_buy_validation.py # Test buy transaction validation
uv run python test_sell_validation.py # Test sell transaction validation
uv run python test_<name>.py         # Run any specific test file
```

### Raycast Integration
```bash
cd raycast-extension
npm install                          # Install Raycast extension dependencies
npm run dev                          # Start Raycast extension in dev mode
```

## Architecture

### High-Level Structure

This is a **FastMCP-based agent** that connects to Google Sheets for live portfolio data, stores historical snapshots in Google Cloud Storage (with local fallback), and provides portfolio analysis tools through the MCP protocol.

**Data Flow:**
1. **Google Sheets** → Live portfolio positions (stocks, bonds, ETFs, pension, cash) + transaction records
2. **Sheets Connector** (`sheets_connector.py`) → Reads positions and currency rates, validates against transaction records
3. **Analysis** (`analysis.py`) → Compares current snapshot with previous, identifies winners/losers/new positions
4. **Storage** (`storage.py` + backends) → Saves snapshots to GCP (primary) and local JSON (backup)
5. **Reporting** (`reporting.py`) → Generates markdown reports with performance summaries
6. **Visualization** (`visualization.py`) → Creates interactive Plotly dashboards with benchmarks

### Storage Architecture (Pluggable Backends)

The system uses a **pluggable storage backend architecture** with three implementations:

1. **HybridStorageBackend** (default) - Dual-write to GCP + local, auto-sync when offline
2. **GCPStorageBackend** - Google Cloud Storage only (europe-north1 region)
3. **LocalFileBackend** - Local JSON files only

All backends implement `StorageBackend` interface defined in `storage_backend.py`. The active backend is determined by `config.yaml` (`storage.backend` setting).

**Key behavior:**
- Hybrid mode always writes to both GCP and local simultaneously
- If GCP fails, queues changes for later sync
- Reads from GCP first, falls back to local if unavailable
- Local backup files stored in `backup/` directory with timestamps

### Transaction Validation System

**Critical feature:** Before creating any portfolio snapshot, the system validates that all buy/sell transactions are properly recorded in the Google Sheets "Transactions" tab.

**How it works:**
1. System compares current portfolio with previous snapshot
2. Detects quantity changes ≥1 share (buys = increase, sells = decrease)
3. Queries "Transactions" sheet for matching records within the time window
4. Validates quantities match (±1 share tolerance)
5. **Blocks snapshot creation** if any transactions are missing/incomplete

**Implementation:**
- `sell_validation.py` - Validates sell transactions (columns A-E)
- `buy_validation.py` - Validates buy transactions (columns J-M)
- Both raise `SellValidationError`/`BuyValidationError` with detailed missing transaction lists
- Integrated into `main.py` `_run_weekly_analysis()` before snapshot save

**Why this matters:** Ensures 100% audit trail for realized gains/losses and cost basis calculations.

### External Data Providers (Abstract Interface Pattern)

The system uses **abstract provider interfaces** for external data sources, making it easy to swap providers:

**Earnings Data:**
- Interface: `earnings_provider.py` (abstract base class)
- Current implementation: `yahoo_earnings_provider.py` (free, no API key)
- Returns standardized `EarningsEvent` models from `earnings_models.py`
- Usage: `events_tracker.py` imports and uses the provider

**Risk Analysis:**
- Uses Alpha Vantage API directly (historical price data)
- Caches data in `cache/` directory for 24 hours
- 12-second delay between API calls to avoid rate limits

**Insider Trading & Short Volume:**
- Uses Fintel.io Web Data API
- Direct API calls in `insider_trading.py` and `short_volume.py`
- All outputs include Fintel attribution as required by terms

### Configuration System (Pydantic v2)

**Two-layer configuration:**
1. `config.yaml` - User-editable YAML file (required fields: `google_sheets.sheet_id`, `ticker_mappings`)
2. `config_models.py` - Pydantic v2 models with validation and defaults

**Key features:**
- Environment variable overrides (prefix: `INVESTMENT_`)
- Nested models for sections (GoogleSheetsConfig, StorageConfig, etc.)
- Sensible defaults for most settings (sheet ranges, currencies, cache TTL)
- Single global config instance via `config.get_config()`

**Example:** `export INVESTMENT_STORAGE_BACKEND=local` overrides `storage.backend` in YAML.

### MCP Tools (FastMCP Server Interface)

All tools are defined in `agent/main.py` using `@mcp.tool()` decorator. Available tools:

**Portfolio Management:**
- `run_portfolio_analysis()` - Full analysis + snapshot + dashboard
- `get_portfolio_status()` - Latest snapshot summary
- `get_portfolio_history_summary()` - Performance since first snapshot
- `get_latest_positions()` - Current positions by category

**Risk & Events:**
- `analyze_portfolio_risk()` - Beta, VaR, correlation matrix, sector exposure
- `get_upcoming_events()` - Earnings calendar (next 60 days)
- `get_earnings_date(ticker)` - Single stock earnings date

**Insider Trading & Short Volume:**
- `get_insider_trades(ticker)` - 90-day insider activity for specific stock
- `get_portfolio_insider_trades()` - Insider activity across all portfolio stocks
- `get_short_volume(ticker, days)` - Short selling data for specific stock
- `get_portfolio_short_analysis()` - Short selling analysis across portfolio

**Visualization:**
- `generate_portfolio_dashboard(time_period)` - Interactive HTML dashboard (7d/30d/90d/1y/all)

**Daily Performance Analysis (NEW):**
- `get_daily_winners()` - Top performing stocks today vs yesterday snapshot
- `get_daily_losers()` - Worst performing stocks today vs yesterday snapshot

### Key Modules

**Core Logic:**
- `main.py` - FastMCP server, MCP tool definitions, orchestration
- `sheets_connector.py` - Google Sheets API integration (reads positions + transactions)
- `analysis.py` - Snapshot comparison, winner/loser calculation, allocation breakdowns
- `reporting.py` - Markdown report generation with emoji formatting
- `storage.py` - Public storage interface (delegates to backends)

**Data Backends:**
- `backends/local_storage.py` - Local JSON file storage with atomic writes
- `backends/gcp_storage.py` - Google Cloud Storage integration
- `backends/hybrid_storage.py` - Combines GCP + local with auto-sync

**External Integrations:**
- `events_tracker.py` - Earnings calendar fetching (uses provider interface)
- `risk_analysis.py` - Portfolio risk metrics (Alpha Vantage historical data)
- `insider_trading.py` - Insider trading analysis (Fintel API)
- `short_volume.py` - Short selling monitoring (Fintel API)
- `visualization.py` - Plotly dashboard generation with benchmark comparisons

**Validation & Models:**
- `sell_validation.py` - Sell transaction validation logic
- `buy_validation.py` - Buy transaction validation logic
- `transaction_models.py` - Pydantic models for transactions
- `config_models.py` - Pydantic v2 configuration schema
- `earnings_models.py` - Earnings event data models

**Raycast Tooling:**
- `raycast_tools.py` - JSON output functions for Raycast scripts
- `raycast-scripts/` - Bash scripts for Raycast Script Commands
- `raycast-extension/` - Native TypeScript Raycast extension

### Credentials & Security

**All credentials stored in macOS Keychain** (never in files or environment variables):

```bash
security find-generic-password -a "mcp-portfolio-agent" -s "google-sheets-credentials" -w  # Service account JSON
security find-generic-password -a "mcp-portfolio-agent" -s "alpha-vantage-api-key" -w      # Alpha Vantage API
security find-generic-password -a "mcp-portfolio-agent" -s "fintel-api-key" -w             # Fintel API
```

Setup scripts available: `setup_keychain.sh`, `setup_alpha_vantage.sh`, `setup_fintel.sh`

### Data Storage Locations

- **Primary:** Google Cloud Storage bucket `investment_snapshots` (europe-north1)
- **Backup:** `portfolio_history.json` (root directory, gitignored)
- **Transactions:** `transactions.json` (root directory, gitignored)
- **Backups:** `backup/` directory (timestamped .bak files, gitignored)
- **Cache:** `cache/` directory (historical prices, 24h TTL, gitignored)
- **Dashboards:** `dashboards/` directory (generated HTML files, gitignored)

## Development Guidelines

### Code Style (from AGENTS.md)

**Key conventions:**
- Python 3.12+, always use double quotes (`"string"`)
- Type hints required on all function signatures
- Google-style docstrings for public functions
- Import order: stdlib, blank line, third-party, blank line, local
- `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Module-level logger: `logger = logging.getLogger(__name__)`
- Never catch bare `except:` - always specific exception types

### Package Management

**Always use `uv` for dependency management** (not pip). The project uses `pyproject.toml` with uv.lock for reproducible builds.

```bash
uv add <package>      # Add new dependency
uv sync               # Install dependencies from lock file
uv run python <file>  # Run Python with virtual environment
```

### Testing Approach

Tests are in root directory as `test_<module>.py` files. No test framework - tests are standalone Python scripts that print results and use assertions.

**When modifying core logic:**
1. Run relevant test file(s) to verify behavior
2. If changing storage: `test_gcp_storage.py`, `test_transaction_storage.py`
3. If changing validation: `test_buy_validation.py`, `test_sell_validation.py`
4. If changing config: `test_config.py`
5. If changing dashboards: `test_dashboard.py`

### Important Patterns

**Configuration access:**
```python
from . import config
cfg = config.get_config()  # Singleton, loads once
sheet_id = cfg.google_sheets.sheet_id
```

**Storage access:**
```python
from . import storage
storage.save_snapshot(snapshot_data)
latest = storage.get_latest_snapshot()
all_snapshots = storage.get_all_snapshots()
```

**Transaction validation (required before snapshot save):**
```python
from .sell_validation import validate_sells_have_transactions, SellValidationError
from .buy_validation import validate_buys_have_transactions, BuyValidationError

try:
    validate_sells_have_transactions(current_snapshot, previous_snapshot, all_transactions)
    validate_buys_have_transactions(current_snapshot, previous_snapshot, all_transactions)
    # Only save if validation passes
    storage.save_snapshot(current_snapshot)
except (SellValidationError, BuyValidationError) as e:
    # Handle missing transactions - block snapshot creation
    raise
```

**Provider pattern (earnings):**
```python
from .earnings_provider import EarningsProvider
from .providers.yahoo_earnings_provider import YahooEarningsProvider

provider: EarningsProvider = YahooEarningsProvider()
events = provider.get_earnings_events(tickers, days_ahead=60)
```

### Google Sheets Structure

The system expects specific sheet structure:

**Main Portfolio Sheet** (default name: "2025", configurable):
- Rows 5-19: US Stocks (columns A-L)
- Rows 20-35: EU Stocks (columns A-L)
- Rows 37-39: Bonds (columns A-L)
- Rows 40-45: ETFs (columns A-L)
- Rows 52-53: Pension (columns A-E)
- Rows 58-60: Cash (columns A-B)
- Cell O2: GBP/EUR exchange rate
- Cell O3: USD/EUR exchange rate

**Transactions Sheet** (separate tab named "Transactions"):
- Columns A-E: Sell transactions (Date, Asset Name, Quantity, Purchase Price, Sell Price)
- Columns J-M: Buy transactions (Date, Asset Name, Quantity, Purchase Price)
- Date format: DD/MM/YYYY
- Prices include currency symbols: £, $, €

**Note:** Ranges are user-configurable in `config.yaml` - these are defaults.

## Common Gotchas

1. **Transaction validation blocks snapshots** - If you see validation errors, you must add missing transactions to Google Sheets before snapshot creation will succeed.

2. **Ticker mappings are case-sensitive** - Asset names in `config.yaml` `ticker_mappings` must match Google Sheets exactly (e.g., "Wise" ≠ "wise").

3. **European stock tickers need exchange suffix** - London = `.L`, Paris = `.PA`, Amsterdam = `.AS` (e.g., `WISE.L`, `ASML.AS`).

4. **Alpha Vantage rate limits** - Risk analysis has 12-second delays between API calls. Expect ~5-10 minutes for full portfolio analysis.

5. **Hybrid storage auto-syncs** - If GCP is unavailable, data is saved locally and auto-uploaded when connection restored. Check `get_storage_status()` to see pending uploads.

6. **Dashboard requires 2+ snapshots** - First run will create snapshot but cannot generate dashboard. Second run creates comparison report and dashboard.

7. **Credentials in Keychain only** - Never hardcode credentials. Use provided setup scripts or `security add-generic-password` commands.

8. **Daily analysis requires yesterday's snapshot** - Tools like `get_daily_winners()` and `get_daily_losers()` need a snapshot from the previous day to exist. They compare today's live data against yesterday's snapshot to calculate daily performance.

## Raycast Integration

Two Raycast interfaces available:

1. **Raycast Scripts** (`raycast-scripts/`) - Bash scripts that call Python directly, output JSON
2. **Raycast Extension** (`raycast-extension/`) - Native TypeScript extension with rich UI

When modifying portfolio logic, ensure changes are reflected in:
- `agent/raycast_tools.py` - Python functions returning JSON for scripts
- `raycast-extension/src/*.tsx` - TypeScript components for native extension
