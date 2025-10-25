# Short Volume Tracking - Setup & Usage

## Overview

The Investment MCP Agent now includes short volume tracking powered by Fintel.io's API. This feature allows you to monitor daily short selling activity for portfolio stocks and identify unusual short selling patterns.

## Features

- **Daily Short Volume Data**: Track short selling activity day by day
- **Trend Analysis**: Identify increasing, decreasing, or stable short selling trends
- **Risk Assessment**: Automatic categorization (High/Medium/Low risk)
- **Portfolio-Wide Analysis**: Analyze all portfolio stocks at once
- **Automatic Filtering**: Only stocks are analyzed (bonds, ETFs, pension, cash excluded)

## What is Short Volume?

**Short Volume** is the number of shares sold short on a given day. The **Short Volume Ratio** is:

```
Short Volume Ratio = (Short Volume / Total Volume) × 100
```

**Example:**
- If 10 million shares of AAPL traded today
- And 2.5 million were short sales
- Short Volume Ratio = 25%

**Interpretation:**
- **< 20%**: Normal short activity
- **20-30%**: Moderate short interest
- **30-40%**: Elevated short activity
- **> 40%**: High short activity (potential squeeze risk)

## Setup

### 1. API Key Already Configured

If you've already set up the Fintel API for insider trading, **you're done!** The same API key works for short volume data.

If not, run:
```bash
./setup_fintel.sh
```

### 2. Verify Setup

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

#### `get_short_volume(ticker: str, days: int = 30)`
Get short volume data for a specific stock.

**Example:**
```python
get_short_volume("TSLA", 30)
```

**Returns:**
- Average short ratio over the period
- 7-day and 30-day averages
- Latest short ratio with date
- Trend (Increasing/Decreasing/Stable)
- Risk level (High/Medium/Low)
- Recent daily activity (last 5 days)

#### `get_portfolio_short_analysis()`
Analyze short selling for all portfolio stocks.

**Example:**
```python
get_portfolio_short_analysis()
```

**Returns:**
- Stocks organized by risk level (High/Medium/Low)
- Average short ratio per stock
- Trend indicators
- Stocks with no data available

### Direct Testing

Test a single ticker:
```bash
uv run python test_short_volume.py TSLA 30
```

Example output:
```
================================================================================
Testing Short Volume for TSLA (last 30 days)
================================================================================

✅ Ticker: TSLA

📊 Metrics (10 days)
  Average Short Ratio: 30.20%
  7-Day Average: 30.29%
  30-Day Average: 30.20%
  Latest (2025-10-24): 30.00%
  Trend: Stable ↔️

⚠️  Risk Analysis
  Risk Level: 🟢 Low
  Description: Normal Short Activity
  Risk Score: 1
  Factors:
    - Moderate short volume ratio (30.2%)

📅 Recent Activity (last 5 days)
  1. 2025-10-24: 26,303,644 / 87,039,068 (30.00%)
  2. 2025-10-23: 39,129,530 / 117,063,474 (33.00%)
  3. 2025-10-22: 22,752,411 / 67,661,314 (34.00%)
  4. 2025-10-21: 17,808,825 / 49,798,825 (36.00%)
  5. 2025-10-20: 10,023,214 / 57,721,345 (17.00%)

================================================================================
```

## How It Works

### Trend Detection

The system compares recent vs older short ratios:

```python
Recent 7-Day Avg vs Previous 7-Day Avg:
- If recent > previous × 1.1 → Increasing ↗️
- If recent < previous × 0.9 → Decreasing ↘️
- Otherwise → Stable ↔️
```

### Risk Scoring

Risk is calculated based on multiple factors:

**Factors Contributing to Risk Score:**
1. **Short Ratio** (0-2 points)
   - > 40% → +2 points (High)
   - > 30% → +1 point (Moderate)
   - < 30% → 0 points (Normal)

2. **Overall Risk Level:**
   - **High Risk (🔴)**: Score ≥ 5 - "Short Squeeze Potential"
   - **Medium Risk (🟡)**: Score 3-4 - "Moderate Short Pressure"
   - **Low Risk (🟢)**: Score < 3 - "Normal Short Activity"

**Note:** Current implementation only uses short volume ratio for scoring. Future versions may add short interest (% of float) and days to cover if API tier is upgraded.

## API Details

- **Endpoint**: `GET https://api.fintel.io/web/v/0.0/ss/{country}/{symbol}`
- **Authentication**: Header-based with `X-API-KEY`
- **Data Scope**: Typically 10+ days of historical data
- **Update Frequency**: Daily (T+1)
- **Attribution**: All outputs include "Data provided by Fintel.io"

## Data Availability

### ✅ Available
- Daily short volume (shares)
- Total volume (shares)
- Short volume ratio (%)
- Historical data (typically 10+ days)

### ❌ Not Available (Current API Tier)
- Short interest (% of float shorted)
- Days to cover ratio
- Settlement date information

To access short interest data, a higher Fintel API tier would be required.

## Example Interpretation

### Low Risk Example (AAPL)
```
Average Short Ratio: 18.5%
Trend: Stable
Risk: Low 🟢
```
**Interpretation:** Normal short activity. No unusual patterns.

### Medium Risk Example (Stock X)
```
Average Short Ratio: 35.2%
Trend: Increasing ↗️
Risk: Medium 🟡
```
**Interpretation:** Elevated short selling. Monitor for further increases.

### High Risk Example (Stock Y)
```
Average Short Ratio: 48.7%
Trend: Increasing ↗️
Risk: High 🔴
```
**Interpretation:** Very high short activity with increasing trend. Potential short squeeze candidate if positive catalyst occurs.

## Troubleshooting

### No Data Available
```
No short volume data available for this ticker.
```

**Possible Causes:**
- Ticker not covered by Fintel
- Invalid ticker symbol
- Non-US stock (some international stocks may have limited data)

**Solution:** Verify ticker symbol and try a well-known US stock like AAPL or TSLA to confirm API access.

### Ticker Not Mapped
```
❌ Missing ticker mappings for the following stocks:
- Tesla Inc

📝 Please add these mappings to ticker_mapping.json
```

**Solution:** Add mapping to `ticker_mapping.json`:
```json
{
  "mappings": {
    "Tesla Inc": "TSLA"
  }
}
```

## Files Created/Modified

- `agent/short_volume.py` - Core module with short volume logic
- `test_short_volume.py` - Testing script
- `agent/main.py` - Added 2 MCP tools
- `README.md` - Updated with short volume features
- `AGENTS.md` - Updated with tool documentation
- `SHORT_VOLUME_PLAN.md` - Implementation plan and API details
- `SHORT_VOLUME_SETUP.md` - This file

## Differences from Insider Trading

| Feature | Insider Trading | Short Volume |
|---------|----------------|--------------|
| **Time Scope** | Last 90 days | Last 10-30 days (varies) |
| **Data Type** | Transaction-level (individual trades) | Daily aggregates |
| **Sentiment** | Buy/Sell ratio | Short ratio trends |
| **Update Frequency** | Real-time (as filed) | Daily (T+1) |
| **Risk Factors** | 2:1 buy/sell ratio | Short volume ratio thresholds |

## Terms of Service

This feature uses Fintel.io's API. All outputs must include the attribution "Data provided by Fintel.io" as required by their terms of service. This attribution is automatically included in all tool outputs.

## Further Reading

- [Short Selling Basics](https://www.investopedia.com/terms/s/shortselling.asp)
- [Understanding Short Interest](https://www.investopedia.com/terms/s/shortinterest.asp)
- [Short Squeeze Explanation](https://www.investopedia.com/terms/s/shortsqueeze.asp)
