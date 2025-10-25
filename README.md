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

### 3. Configure Sheet Details

Edit `sheet-details.json` with your Google Sheet ID and settings.

### 4. Configure Ticker Mappings

Edit `ticker_mapping.json` to map your portfolio stock names to ticker symbols:

```json
{
  "mappings": {
    "Apple Inc": "AAPL",
    "Microsoft Corporation": "MSFT",
    "ASML Holding": "ASML.AS",
    "Wise": "WISE.L"
  }
}
```

For European stocks, include the exchange suffix (e.g., `.L` for London, `.PA` for Paris).

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

**Sheet Not Found**: Verify `sheetId` in `sheet-details.json`

**Stock Not Mapped**: Add the stock to `ticker_mapping.json` in the "mappings" section

**Alpha Vantage Rate Limits**: Free tier allows 5 calls/minute

**Debug Mode**:
```bash
export LOG_LEVEL=DEBUG
uv run python -m agent.main
```

## Security Benefits

- Credentials stored in macOS Keychain (never in plain text)
- No risk of accidental credential commits
- Service Account provides granular permission control
- Audit trail of all access
- Revocable access without changing credentials

## Data Storage

- **File**: `portfolio_history.json`
- **Format**: Array of timestamped snapshots
- **Retention**: All historical data (no automatic cleanup)

## Technical Stack

- **Language**: Python 3.12+
- **Framework**: FastMCP
- **APIs**: Google Sheets API, Alpha Vantage API
- **Storage**: JSON file persistence
- **Security**: macOS Keychain
- **Package Manager**: uv