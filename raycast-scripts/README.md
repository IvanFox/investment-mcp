# Investment Portfolio - Raycast Scripts

Quick access to portfolio analytics directly from Raycast with JSON output.

## Overview

These Raycast Script Commands provide instant access to your investment portfolio data:
- **Live data** from Google Sheets (current positions)
- **Historical comparisons** between snapshots
- **Earnings calendars** and insider trading activity
- **JSON output** for structured data viewing

All scripts are **read-only** - they never create snapshots or modify data.

---

## Prerequisites

1. **uv package manager** installed
2. **Configured investment-mcp** project:
   - `config.yaml` with Google Sheets ID and ticker mappings
   - Credentials in macOS Keychain (Google Sheets, Alpha Vantage, Fintel)
3. **Raycast** application installed

---

## Installation

### 1. Ensure MCP Server is Configured

```bash
cd /path/to/investment-mcp
uv sync
python check_setup.py  # Verify configuration
```

### 2. Add Scripts to Raycast

1. Open Raycast Settings (Cmd+,)
2. Navigate to **Extensions → Script Commands**
3. Click **Add Directory**
4. Select: `/path/to/investment-mcp/raycast-scripts/`
5. Scripts will appear in Raycast immediately

### 3. Verify Scripts

Open Raycast (Cmd+Space) and type "Portfolio" - you should see all 6 commands.

---

## Available Scripts

### 📊 Portfolio Status
**Command:** Portfolio Status  
**Icon:** 💼  
**Speed:** ~2-3 seconds  
**Data Source:** Google Sheets (live)

**Description:**  
View current portfolio holdings fetched live from your spreadsheet. Shows all positions sorted by value (largest first) within each category.

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "total_value_eur": 405303.56,
    "asset_count": 42,
    "categories": {
      "EU Stocks": {
        "value": 195097.56,
        "percentage": 48.1,
        "count": 15,
        "positions": [
          {
            "name": "ASML Holding",
            "quantity": 42.0,
            "current_value_eur": 15234.50,
            "gain_loss_eur": 3234.50,
            "gain_loss_pct": 26.95
          }
        ]
      }
    }
  }
}
```

**Use Case:** "What do I currently own?" / "Show me my positions"

---

### ⚡ Quick Analysis
**Command:** Quick Analysis  
**Icon:** 📊  
**Speed:** ~2-3 seconds  
**Data Source:** Google Sheets (live) + Latest Snapshot

**Description:**  
Compare your current portfolio (live from spreadsheet) against the last saved snapshot. Shows how your portfolio has changed since the last analysis, including top gainers and losers.

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "current_status": {
      "total_value_eur": 407500.00,
      "timestamp": "2025-12-27T10:00:00Z"
    },
    "snapshot_comparison": {
      "snapshot_date": "2025-12-20T08:30:00Z",
      "days_ago": 7,
      "value_change": {
        "eur": 2196.44,
        "percentage": 0.54,
        "direction": "up"
      }
    },
    "winners": [...],
    "losers": [...]
  }
}
```

**Use Case:** "How has my portfolio changed since last analysis?"

**Note:** Requires at least one snapshot. If no snapshot exists, returns current status only with a message to run `run_portfolio_analysis()` first.

---

### 📈 Winners & Losers
**Command:** Winners & Losers  
**Icon:** 📈  
**Speed:** <1 second  
**Data Source:** Last 2 Snapshots (storage)

**Description:**  
Historical comparison showing top movers between your last two saved snapshots. Faster than Quick Analysis since it doesn't fetch live data.

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "comparison_period": {
      "from": "2025-12-13T08:30:00Z",
      "to": "2025-12-20T08:30:00Z",
      "days": 7
    },
    "portfolio_change": {
      "value_eur": 2600.00,
      "percentage": 4.39,
      "direction": "up"
    },
    "winners": [...],
    "losers": [...]
  }
}
```

**Use Case:** "What changed between my last two analyses?"

**Note:** Requires at least 2 snapshots.

---

### 📅 Upcoming Events
**Command:** Upcoming Events  
**Icon:** 📅  
**Speed:** ~3-5 seconds  
**Data Source:** Google Sheets + Yahoo Finance API

**Description:**  
Earnings calendar for all portfolio stocks. Shows upcoming earnings reports within the next 60 days, sorted chronologically.

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "events": [
      {
        "type": "Earnings Report",
        "ticker": "AAPL",
        "company_name": "Apple Inc",
        "date": "2025-01-30",
        "days_until": 34,
        "estimate": 2.35
      }
    ],
    "total_events": 8,
    "provider": "Yahoo Finance"
  }
}
```

**Use Case:** "When are my stocks reporting earnings?"

---

### 🔍 Insider Trades (Portfolio)
**Command:** Insider Trades (Portfolio)  
**Icon:** 🔍  
**Speed:** ~5-10 seconds  
**Data Source:** Google Sheets + Fintel API

**Description:**  
Insider trading activity for all portfolio stocks over the last 90 days. Shows which stocks have significant insider buying or selling, organized by sentiment (Bullish/Neutral/Bearish).

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "stocks_analyzed": 15,
    "stocks_with_activity": 8,
    "total_transactions": 45,
    "by_sentiment": {
      "Bullish": [
        {
          "ticker": "AAPL",
          "total_trades": 12,
          "statistics": {
            "total_buys": 10,
            "total_sells": 2,
            "net_sentiment": "Bullish"
          }
        }
      ]
    }
  }
}
```

**Use Case:** "Are insiders buying or selling my stocks?"

**Note:** Excludes bonds, ETFs, pension, and cash positions.

---

### 🔎 Insider Trades (Ticker)
**Command:** Insider Trades (Ticker)  
**Icon:** 🔎  
**Speed:** ~2-3 seconds  
**Data Source:** Fintel API  
**Argument:** Ticker symbol (e.g., AAPL)

**Description:**  
Insider trading activity for a specific stock ticker over the last 90 days. Shows recent transactions and sentiment analysis.

**Usage:**
```
Type in Raycast: Insider Trades (Ticker)
Enter ticker: AAPL
```

**Output Structure:**
```json
{
  "success": true,
  "data": {
    "ticker": "AAPL",
    "total_trades": 12,
    "statistics": {
      "total_buys": 10,
      "total_sells": 2,
      "buy_value_usd": 5000000,
      "sell_value_usd": 500000,
      "net_sentiment": "Bullish"
    },
    "trades": [...]
  }
}
```

**Use Case:** "What are insiders doing with AAPL?"

---

## Script Comparison

| Script | Live Data? | Snapshot? | Speed | Use Case |
|--------|-----------|-----------|-------|----------|
| Portfolio Status | ✅ Yes | ❌ No | ~2-3s | Current holdings |
| Quick Analysis | ✅ Yes | ✅ Latest | ~2-3s | Recent changes |
| Winners & Losers | ❌ No | ✅ Last 2 | <1s | Historical trend |
| Upcoming Events | ✅ Yes | ❌ No | ~3-5s | Earnings calendar |
| Insider Trades (Portfolio) | ✅ Yes | ❌ No | ~5-10s | Portfolio insider activity |
| Insider Trades (Ticker) | N/A | ❌ No | ~2-3s | Single stock insider check |

---

## Troubleshooting

### Script Not Appearing in Raycast

**Symptoms:** Scripts don't show up in Raycast after adding directory

**Solutions:**
1. Verify directory is added: Raycast Settings → Extensions → Script Commands
2. Check script permissions: `chmod +x raycast-scripts/*.py`
3. Restart Raycast: Cmd+Q, then reopen

---

### "Failed to fetch portfolio data" Error

**Symptoms:** Error when running Portfolio Status or Quick Analysis

**Solutions:**
1. Verify `config.yaml` has correct `sheet_id`
2. Check Google Sheets credentials in keychain:
   ```bash
   security find-generic-password -a "mcp-portfolio-agent" -s "google-sheets-credentials" -w
   ```
3. Ensure service account has access to Google Sheet
4. Test manually: `uv run python -m agent.main`

---

### "No snapshot available" in Quick Analysis

**Symptoms:** Quick Analysis returns message about no snapshot

**Solution:**  
Run portfolio analysis first to create a snapshot:
```bash
uv run python server.py
# Then call run_portfolio_analysis() via MCP client
```

Or use the existing `run_portfolio_analysis()` MCP tool.

---

### API Rate Limit Errors

**Symptoms:** "Rate limit exceeded" or "429" errors

**Solutions:**
- **Alpha Vantage:** Free tier = 5 calls/minute, 500 calls/day
- **Fintel:** Check your plan limits
- **Yahoo Finance:** Usually no strict limits, but can throttle heavy usage
- Wait a few minutes and retry
- Consider upgrading API tier for higher limits

---

### Import/Module Errors

**Symptoms:** "Module not found" or import errors

**Solutions:**
1. Ensure dependencies installed: `uv sync`
2. Run from project root directory
3. Check Python version: `python --version` (requires 3.12+)

---

## Performance Notes

- **Portfolio Status:** Fetches live data from Google Sheets (~2-3s)
- **Quick Analysis:** Fetches live + compares with snapshot (~2-3s)
- **Winners/Losers:** No API calls, uses stored snapshots (<1s)
- **Upcoming Events:** Fetches from Yahoo Finance for all stocks (~3-5s)
- **Insider Trades (Portfolio):** Multiple API calls to Fintel (~5-10s)
- **Insider Trades (Ticker):** Single API call to Fintel (~2-3s)

**Tip:** For fastest results, use Winners/Losers (no network calls).

---

## FAQ

### Q: Do these scripts create snapshots?
**A:** No, all scripts are read-only. Only `run_portfolio_analysis()` (from MCP server) creates snapshots.

### Q: What's the difference between Quick Analysis and Winners/Losers?
**A:** 
- **Quick Analysis:** Compares live data (spreadsheet) vs last snapshot
- **Winners/Losers:** Compares last two snapshots (historical)

Quick Analysis shows "current vs last analysis", Winners/Losers shows "analysis N vs analysis N-1".

### Q: Can I customize the number of winners/losers shown?
**A:** Currently fixed at 5. To change, edit the script and modify the `limit` parameter in the function call.

### Q: Why is Insider Trades (Portfolio) slow?
**A:** It makes separate API calls to Fintel for each stock in your portfolio. With 15 stocks, that's 15 API requests. This is necessary to get detailed data for each position.

### Q: Do I need all the API keys for all scripts?
**A:**
- **Google Sheets:** Required for all scripts that fetch portfolio data
- **Alpha Vantage:** Not required for Raycast scripts (used by risk analysis only)
- **Fintel:** Only required for Insider Trades scripts

### Q: Can I run these scripts outside of Raycast?
**A:** Yes! All scripts are standalone Python scripts:
```bash
cd /path/to/investment-mcp
uv run python raycast-scripts/portfolio-status.py
```

---

## Example Workflows

### Morning Portfolio Check
1. **Quick Analysis** - See overnight changes
2. **Upcoming Events** - Check today's earnings reports

### Weekly Review
1. **Portfolio Status** - Current holdings snapshot
2. **Winners & Losers** - Performance vs last week
3. **Insider Trades (Portfolio)** - Recent insider activity

### Research Specific Stock
1. **Insider Trades (Ticker)** - Check insider sentiment
2. **Upcoming Events** - Find next earnings date

---

## Technical Details

### Architecture
- **Language:** Python 3.12+
- **Package Manager:** uv
- **Output Format:** JSON
- **Data Sources:** Google Sheets, Yahoo Finance, Fintel
- **Storage:** GCP Storage (primary) + Local (fallback)

### File Structure
```
raycast-scripts/
├── lib/
│   ├── raycast_client.py              # Client for agent functions
│   ├── json_formatter.py              # JSON output formatting
│   ├── error_handler.py               # Error handling
│   ├── portfolio-status_impl.py       # Portfolio status implementation
│   ├── quick-analysis_impl.py         # Quick analysis implementation
│   ├── portfolio-winners-losers_impl.py # Winners/losers implementation
│   ├── upcoming-events_impl.py        # Events implementation
│   ├── insider-trades-portfolio_impl.py # Portfolio insiders implementation
│   └── insider-trades-ticker_impl.py  # Ticker insiders implementation
├── portfolio-status              # Bash wrapper → portfolio-status_impl.py
├── quick-analysis                # Bash wrapper → quick-analysis_impl.py
├── portfolio-winners-losers      # Bash wrapper → portfolio-winners-losers_impl.py
├── upcoming-events               # Bash wrapper → upcoming-events_impl.py
├── insider-trades-portfolio      # Bash wrapper → insider-trades-portfolio_impl.py
└── insider-trades-ticker         # Bash wrapper → insider-trades-ticker_impl.py
```

**Architecture:**
- **Bash wrappers** (no `.py` extension): Executable scripts that Raycast recognizes
- **Python implementations** (`lib/*_impl.py`): Actual Python logic
- Each wrapper sets the correct working directory and calls `uv run python3` with the implementation file

This two-layer approach ensures:
- ✅ Works reliably with Raycast (no exec format errors)
- ✅ Python code stays in `.py` files (easy to edit and test)
- ✅ Scripts work from any directory
- ✅ Clean separation of concerns

---

## Support

For issues or questions:
1. Check this README first
2. Verify setup with `python check_setup.py`
3. Review main project README.md
4. Check logs: scripts output errors to stderr

---

## Updates

When the main investment-mcp project is updated:
```bash
cd /path/to/investment-mcp
uv sync  # Update dependencies
# Scripts will automatically use updated code
```

No need to update Raycast or reinstall scripts - they use the agent modules directly.

---

**Enjoy your portfolio analytics! 📊💼**
