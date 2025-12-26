# Investment MCP Agent

An automated portfolio monitoring and performance analysis system built with FastMCP that tracks your complete investment portfolio including stocks, bonds, ETFs, pension, and cash positions across multiple currencies.

## Features

- **Complete Portfolio Tracking**: Stocks (US & EU), Bonds, ETFs, Pension (2nd/3rd pillar), Cash positions
- **Multi-Currency Support**: USD, EUR, GBP with automatic conversion
- **Performance Analysis**: Week-over-week comparison with top/bottom movers
- **Portfolio Allocation**: Breakdown by 6 asset categories
- **Upcoming Events**: Earnings reports from Alpha Vantage API
- **Risk Analysis**: Beta, VaR, concentration risk, correlation matrix, sector exposure
- **Insider Trading**: Track insider buys/sells for portfolio stocks via Fintel API
- **Short Volume Tracking**: Monitor short selling activity and trends via Fintel API
- **Rich Reporting**: Markdown reports with detailed breakdowns
- **Secure Storage**: macOS Keychain for all credentials
- **MCP Integration**: FastMCP tools for portfolio management
- **Persistent History**: JSON-based storage with full audit trail

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Credentials

#### Google Sheets (Service Account)

Store your Google Cloud Service Account JSON credentials in macOS Keychain:

```bash
# Automated setup (recommended)
./setup_keychain.sh path/to/your-service-account.json

# Or manual setup
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat your-service-account.json | xxd -p | tr -d '\n')" \
  -T ""
```

**Important**: Share your Google Sheet with the service account email found in your JSON file (e.g., `investment-mcp@your-project.iam.gserviceaccount.com`)

#### Alpha Vantage API (Events & Risk Analysis)

Store your Alpha Vantage API key for earnings tracking and risk analysis:

```bash
# Automated setup (recommended)
./setup_alpha_vantage.sh

# Or manual setup
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "alpha-vantage-api-key" \
  -w "YOUR_API_KEY_HERE" \
  -U
```

#### Fintel API (Insider Trading)

Store your Fintel API key for insider trading data:

```bash
# Automated setup (recommended)
./setup_fintel.sh

# Or manual setup
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "fintel-api-key" \
  -w "YOUR_API_KEY_HERE" \
  -U
```

### 3. Configure Application Settings

Copy the example configuration and edit it with your settings:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your Google Sheet ID and ticker mappings
```

The `config.yaml` file contains all application settings:

```yaml
google_sheets:
  sheet_id: YOUR_GOOGLE_SHEET_ID_HERE

storage:
  backend: hybrid  # Options: hybrid, gcp, local
  gcp:
    bucket_name: investment_snapshots
    credentials_source: keychain
  local:
    file_path: ./portfolio_history.json

ticker_mappings:
  Apple Inc: AAPL
  Microsoft Corporation: MSFT
  ASML Holding: ASML.AS
  Wise: WISE.L
```

For European stocks, include the exchange suffix (e.g., `.L` for London, `.PA` for Paris, `.AS` for Amsterdam).

#### Environment Variable Overrides

You can override any config value using environment variables:

```bash
export INVESTMENT_SHEET_ID="your-sheet-id"
export INVESTMENT_GCP_BUCKET="custom-bucket-name"
export INVESTMENT_STORAGE_BACKEND="local"  # or "gcp" or "hybrid"
export INVESTMENT_LOG_LEVEL="DEBUG"  # or "INFO", "WARNING", "ERROR"
```

### 5. Verify Setup

```bash
python check_setup.py
```

## Usage

### Running the MCP Server (Recommended)

```bash
uv run python server.py
```

Available MCP tools:
- `run_portfolio_analysis()` - Trigger portfolio analysis and generate report
- `get_portfolio_status()` - Get current portfolio status
- `get_portfolio_history_summary()` - View historical performance
- `get_latest_positions()` - View all current positions organized by category
- `get_upcoming_events()` - Fetch upcoming earnings reports (next 2 months)
- `analyze_portfolio_risk()` - Perform comprehensive risk analysis
- `get_insider_trades(ticker)` - Get insider trading activity for a specific stock
- `get_portfolio_insider_trades()` - Get insider trading for all portfolio stocks
- `get_short_volume(ticker, days)` - Get short selling activity for a specific stock
- `get_portfolio_short_analysis()` - Analyze short selling across portfolio stocks

### Direct Analysis

```bash
# Portfolio analysis
uv run python -m agent.main

# Upcoming events
uv run python run_events.py
```

## Google Sheets Structure

Your Google Sheet should follow this structure:

**Sheet Name**: `2025` (configurable in `agent/sheets_connector.py`)

**Currency Rates**:
- Cell O2: GBP/EUR rate
- Cell O3: USD/EUR rate

**Asset Ranges**:
- A5:L19 - US Stocks
- A20:L35 - EU Stocks
- A37:L39 - Bonds
- A40:L45 - ETFs
- A52:E53 - Pension schemes (2nd and 3rd pillar)
- A58:B60 - Cash positions

**Column Structure**:
- Column A: Asset/Position name
- Column B: Quantity (for stocks/bonds/ETFs)
- Column D: Purchase Price per Unit (with currency symbol: $, €, £)
- Column E: Current Price per Unit (with currency symbol: $, €, £)

**Pension Data**:
- Column A: Pension scheme name (e.g., "II level", "III level")
- Column E: Current value (with € symbol)

**Cash Data**:
- Column A: Currency name (e.g., "USD", "EUR", "GBP")
- Column B: Cash amount (numeric value)

The system automatically detects currency from symbols and converts all values to EUR.

## Sample Output

```markdown
# 📊 Weekly Portfolio Performance Report

## 💰 Portfolio Summary
**Current Total Value:** €61,800.00
**Weekly Change:** 📈 +€2,600.00 (+4.39%)

## 🚀 Top Performers
1. **Vanguard S&P 500 ETF**: +€500.00
2. **Apple Inc**: +€500.00

## 📉 Underperformers
1. **Microsoft Corp**: €-400.00

## 🆕 New Positions
- **Tesla Inc**: 30 shares, €9,500.00

## 💸 Sold Positions
- **ASML Holding**: 💔 €-500.00

## 📊 Portfolio Allocation
- **EU Stocks**: €195,097.56 (48.1%)
- **Pension**: €93,000.00 (22.9%)
- **US Stocks**: €40,478.60 (10.0%)
- **Cash**: €35,850.45 (8.8%)
- **ETFs**: €34,236.95 (8.4%)
- **Bonds**: €6,640.00 (1.6%)
```

## Troubleshooting

**Keychain Access Denied**:
```bash
# Verify credentials exist
security find-generic-password -a "mcp-portfolio-agent" -s "google-sheets-credentials" -w
security find-generic-password -a "mcp-portfolio-agent" -s "alpha-vantage-api-key" -w
```

**Permission Denied**: Share your Google Sheet with the service account email from your credentials

**Config File Missing**: Run `cp config.yaml.example config.yaml` and edit with your settings

**Sheet Not Found**: Verify `google_sheets.sheet_id` in `config.yaml`

**Stock Not Mapped**: Add the stock to `ticker_mappings` section in `config.yaml`

**Alpha Vantage Rate Limits**: Free tier allows 5 calls/minute

**Debug Mode**:
```bash
export INVESTMENT_LOG_LEVEL=DEBUG
uv run python -m agent.main
```

**Test Configuration**:
```bash
# Verify config loads correctly
uv run python -c "from agent import config; cfg = config.get_config(); print(f'✅ Config loaded: {len(cfg.ticker_mappings)} mappings')"

# Run comprehensive config tests
uv run python test_config.py
```

## Security Benefits

- Credentials stored in macOS Keychain (never in plain text)
- No risk of accidental credential commits
- Service Account provides granular permission control
- Audit trail of all access
- Revocable access without changing credentials

## Data Storage

Portfolio history is stored in **Google Cloud Storage** for automatic cross-machine synchronization:

- **Primary Storage**: Google Cloud Storage bucket `investment_snapshots` (europe-north1)
- **Backup Storage**: Local file `portfolio_history.json` (automatic dual-write)
- **Format**: JSON array of timestamped snapshots
- **Retention**: All historical data (no automatic cleanup)
- **Sync**: Automatic with fallback to local when offline

### Storage Behavior

The system uses a **hybrid storage backend** with intelligent fallback:

1. **Normal Operation**: Saves to both GCP and local file simultaneously
2. **Offline Mode**: If GCP unavailable, saves locally and queues for retry
3. **Auto-Sync**: When GCP becomes available, automatically uploads queued snapshots
4. **Read Priority**: Always reads from GCP when available, falls back to local

### Checking Storage Status

Use the MCP tool to check storage backend status:

```python
get_storage_status()  # Shows GCP availability, sync status, pending uploads
```

### Manual Access

**View data in GCP:**
```bash
# Using gsutil (if installed)
gsutil cat gs://investment_snapshots/portfolio_history.json

# Using gcloud
gcloud storage cat gs://investment_snapshots/portfolio_history.json
```

**View local backup:**
```bash
cat portfolio_history.json
```

### Migration

If you have existing local data, migrate it to GCP:

```bash
uv run python migrate_to_gcp.py
```

This uploads your existing `portfolio_history.json` to Google Cloud Storage.

## Technical Stack

- **Language**: Python 3.12+
- **Framework**: FastMCP
- **APIs**: Google Sheets API, Alpha Vantage API, Fintel API, Yahoo Finance
- **Storage**: Google Cloud Storage (primary) + Local JSON (backup)
- **Security**: macOS Keychain
- **Package Manager**: uv