# Insider Trading Feature - Setup & Usage

## Overview

The Investment MCP Agent now includes insider trading tracking powered by Fintel.io's Web Data API. This feature allows you to monitor insider buying and selling activity for portfolio stocks over the last 90 days.

## Features

- **Single Stock Analysis**: Track insider trades for any ticker
- **Portfolio-Wide Analysis**: Analyze all portfolio stocks at once
- **Sentiment Analysis**: Automatic categorization (Bullish/Neutral/Bearish)
- **Recent Transactions**: View detailed transaction history
- **Automatic Filtering**: Only stocks are analyzed (bonds, ETFs, pension, cash excluded)

## Setup

### 1. Get a Fintel API Key

Sign up for a Fintel API account at https://fintel.io and obtain your API key.

### 2. Store API Key in Keychain

Run the setup script:

```bash
./setup_fintel.sh
```

Or manually:

```bash
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "fintel-api-key" \
  -w "YOUR_API_KEY_HERE" \
  -U
```

### 3. Verify Setup

```bash
python check_setup.py
```

You should see:
```
✅ Fintel API Key: sk_xxxx...
```

## Usage

### Via MCP Server

Start the server:
```bash
uv run python server.py
```

Available tools:

#### `get_insider_trades(ticker: str)`
Get insider trading activity for a specific stock.

**Example:**
```python
get_insider_trades("AAPL")
```

**Returns:**
- Total transactions (last 90 days)
- Buy/sell counts and values
- Net sentiment (Bullish/Neutral/Bearish)
- Recent transaction details

#### `get_portfolio_insider_trades()`
Analyze insider trading for all portfolio stocks.

**Example:**
```python
get_portfolio_insider_trades()
```

**Returns:**
- Stocks organized by sentiment
- Summary statistics per stock
- Stocks with no recent activity

### Direct Testing

Test a single ticker:
```bash
uv run python test_insider_trading.py AAPL
```

## How It Works

### Sentiment Calculation

The sentiment is determined by comparing buy vs sell values:

- **Bullish**: Buy value > 2x Sell value
- **Bearish**: Sell value > 2x Buy value  
- **Neutral**: Neither condition met

### Transaction Types

The API reports various transaction types:
- **Sale/Buy**: Direct stock purchases/sales
- **OptionEx**: Option exercises (counted as buys)
- **TaxPay**: Tax withholding (counted as sells)

### Country Detection

The system automatically detects country codes from ticker symbols:

| Ticker Suffix | Country | Example |
|--------------|---------|---------|
| `.L` | UK | WISE.L |
| `.AS` | Netherlands | ASML.AS |
| `.PA` | France | MC.PA |
| `.DE` | Germany | SAP.DE |
| (none) | US | AAPL |

## API Details

- **Endpoint**: `GET https://api.fintel.io/web/v/0.0/n/{country}/{symbol}`
- **Authentication**: Header-based with `X-API-KEY`
- **Rate Limits**: Check your Fintel plan details
- **Data Scope**: Last 90 days of insider trades
- **Attribution**: All outputs include "Data provided by Fintel.io"

## Example Output

```markdown
# 📊 Insider Trading - AAPL

## Summary (Last 90 Days)

**Total Transactions:** 25
**Buy Transactions:** 5
**Sell Transactions:** 20

**Total Buy Value:** $0.00
**Total Sell Value:** $134,912,124.11
**Net Sentiment:** Bearish

## Recent Transactions

**2025-10-16** - Parekh Kevan
- Type: Sale
- Shares: -500
- Value: $-124,365.00

**2025-10-16** - Parekh Kevan
- Type: Sale
- Shares: -1,534
- Value: $-380,155.88

---
**Data URL:** https://fintel.io/n/us/aapl
**As of:** 2025-10-25T18:07:27+00:00

*Data provided by [Fintel.io](https://fintel.io)*
```

## Troubleshooting

### API Key Not Found
```
❌ Fintel API key error: Failed to retrieve Fintel API key from Keychain
💡 Run: ./setup_fintel.sh
```

**Solution**: Store your API key using `./setup_fintel.sh`

### Ticker Not Mapped
```
❌ Missing ticker mappings for the following stocks:
- Apple Inc
- Microsoft Corporation

📝 Please add these mappings to ticker_mapping.json
```

**Solution**: Add mappings to `ticker_mapping.json`:
```json
{
  "mappings": {
    "Apple Inc": "AAPL",
    "Microsoft Corporation": "MSFT"
  }
}
```

### No Data Available
```
No insider trading activity found in the last 90 days.
```

This is normal if:
- The stock has no recent insider trades
- The ticker is invalid
- The stock is not covered by Fintel

## Files Created/Modified

- `agent/insider_trading.py` - Core module with insider trading logic
- `setup_fintel.sh` - API key setup script
- `test_insider_trading.py` - Testing script
- `agent/main.py` - Added MCP tools
- `README.md` - Updated with Fintel setup
- `AGENTS.md` - Updated with tool documentation
- `check_setup.py` - Added Fintel key verification

## Terms of Service

This feature uses Fintel.io's Web Data API. All outputs must include the attribution "Data provided by Fintel.io" as required by their terms of service. This attribution is automatically included in all tool outputs.
