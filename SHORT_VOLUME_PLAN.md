# Security Short Volume Feature - Implementation Plan

## Overview

Add short volume tracking to the Investment MCP Agent using Fintel.io's API. This feature will allow monitoring of short selling activity for portfolio stocks.

## Fintel API Endpoints for Short Volume

Based on Fintel's API documentation, the following endpoints are available:

### 1. Short Volume Data
**Endpoint**: `GET https://api.fintel.io/api/v1/shortVolume/{country}/{symbol}`
- Returns daily short volume data
- Includes short volume, total volume, short volume ratio
- Historical data available

### 2. Short Interest Data  
**Endpoint**: `GET https://api.fintel.io/api/v1/shortInterest/{country}/{symbol}`
- Returns short interest as percentage of float
- Shows days to cover ratio
- Updated bi-monthly (settlement dates)

### 3. Short Squeeze Scores
**Endpoint**: `GET https://api.fintel.io/api/v1/shortSqueeze/{country}/{symbol}`
- Proprietary short squeeze probability score
- Combines short interest, volume, price action

## Proposed Features

### Feature 1: Daily Short Volume Tracking
Track short selling activity on a daily basis:
- Short volume (shares sold short)
- Total volume (total shares traded)
- Short volume ratio (short volume / total volume)
- Trend analysis (7-day, 30-day averages)

### Feature 2: Short Interest Analysis
Monitor overall short interest positioning:
- Current short interest (% of float)
- Days to cover ratio
- Change over time
- Comparison to historical levels

### Feature 3: Portfolio Short Exposure
Analyze short selling across entire portfolio:
- Stocks ranked by short volume ratio
- Stocks with increasing/decreasing short interest
- Alert on unusual short activity
- Aggregate portfolio short exposure

## Implementation Plan

### Phase 1: Core Module (`agent/short_volume.py`)

#### Functions to Implement:

1. **`load_fintel_api_key()`** ✓ (Already exists in insider_trading.py, can reuse)

2. **`fetch_short_volume(ticker: str, api_key: str, days: int = 30)`**
   - Fetch daily short volume data
   - Returns last N days of data
   - Handles API errors and rate limits

3. **`fetch_short_interest(ticker: str, api_key: str)`**
   - Fetch current short interest data
   - Returns % of float, days to cover
   - Includes historical comparison

4. **`calculate_short_metrics(short_volume_data: List[Dict])`**
   - Calculate 7-day average short ratio
   - Calculate 30-day average short ratio
   - Detect trend (increasing/decreasing)
   - Identify unusual spikes

5. **`analyze_short_risk(short_interest: float, short_ratio: float, days_to_cover: float)`**
   - Calculate short squeeze risk score
   - Categorize risk level (Low/Medium/High)
   - Consider multiple factors

6. **`get_short_volume_for_ticker(ticker: str, days: int = 30)`**
   - Main function for single ticker analysis
   - Combines short volume and short interest
   - Returns comprehensive analysis

7. **`get_portfolio_short_analysis(portfolio_assets: List[Dict])`**
   - Analyze all portfolio stocks
   - Rank by short activity
   - Identify high-risk positions
   - Aggregate portfolio metrics

### Phase 2: MCP Tools (`agent/main.py`)

#### Tools to Add:

1. **`get_short_volume(ticker: str, days: int = 30)`**
   ```python
   """
   Get short volume data for a specific stock ticker.
   
   Shows daily short selling activity over the specified period,
   including short volume ratio, trends, and risk assessment.
   
   Args:
       ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
       days: Number of days to look back (default: 30)
   
   Returns:
       str: Formatted short volume report with metrics and analysis
   """
   ```

2. **`get_short_interest(ticker: str)`**
   ```python
   """
   Get short interest data for a specific stock ticker.
   
   Shows current short interest as percentage of float, days to cover,
   and historical comparison to identify trends.
   
   Args:
       ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
   
   Returns:
       str: Formatted short interest report
   """
   ```

3. **`get_portfolio_short_analysis()`**
   ```python
   """
   Analyze short selling activity across all portfolio stocks.
   
   Identifies stocks with high short interest, unusual short volume,
   and potential short squeeze candidates. Only analyzes stocks
   (excludes bonds, ETFs, pension, cash).
   
   Returns:
       str: Formatted portfolio-wide short analysis
   """
   ```

### Phase 3: Support Files

1. **Testing Script**: `test_short_volume.py`
   - Test single ticker short volume
   - Test short interest
   - Test portfolio analysis

2. **Documentation**: Update existing docs
   - `README.md` - Add short volume features
   - `AGENTS.md` - Document new MCP tools
   - `SHORT_VOLUME_SETUP.md` - Detailed setup guide

3. **Setup Verification**: Update `check_setup.py`
   - Already checks Fintel API key ✓
   - Add short volume API test

## Data Structure Examples

### Short Volume Response
```json
{
  "symbol": "AAPL",
  "country": "US",
  "data": [
    {
      "date": "2025-10-24",
      "shortVolume": 12500000,
      "totalVolume": 45000000,
      "shortVolumeRatio": 0.278
    },
    {
      "date": "2025-10-23",
      "shortVolume": 11800000,
      "totalVolume": 42000000,
      "shortVolumeRatio": 0.281
    }
  ]
}
```

### Short Interest Response
```json
{
  "symbol": "AAPL",
  "country": "US",
  "shortInterest": 112000000,
  "sharesFloat": 15280000000,
  "shortPercentOfFloat": 0.733,
  "daysToCover": 2.5,
  "settlementDate": "2025-10-15",
  "previousShortInterest": 108000000,
  "change": 4000000,
  "changePercent": 3.7
}
```

## Risk Assessment Logic

### Short Squeeze Risk Scoring

**High Risk** (Short Squeeze Potential):
- Short % of float > 20%
- Days to cover > 5 days
- Short ratio > 40% (sustained)
- Recent increase in short interest

**Medium Risk**:
- Short % of float 10-20%
- Days to cover 3-5 days
- Short ratio 30-40%
- Stable short interest

**Low Risk**:
- Short % of float < 10%
- Days to cover < 3 days
- Short ratio < 30%
- Decreasing short interest

## Output Examples

### Single Ticker Short Volume Report
```markdown
# 📊 Short Volume Analysis - AAPL

## Current Metrics (30 Days)

**Average Short Ratio:** 28.5%
**Latest Short Ratio:** 27.8% (Oct 24)
**7-Day Average:** 29.1%
**30-Day Average:** 28.5%

**Trend:** Stable ↔️

## Recent Activity (Last 5 Days)

**Oct 24, 2025**
- Short Volume: 12,500,000 shares
- Total Volume: 45,000,000 shares  
- Short Ratio: 27.8%

**Oct 23, 2025**
- Short Volume: 11,800,000 shares
- Total Volume: 42,000,000 shares
- Short Ratio: 28.1%

## Short Interest

**Short % of Float:** 0.73%
**Days to Cover:** 2.5 days
**Change from Previous:** +3.7%

**Short Squeeze Risk:** Low 🟢

---
*Data provided by [Fintel.io](https://fintel.io)*
```

### Portfolio Short Analysis Report
```markdown
# 📊 Portfolio Short Volume Analysis

## Summary

**Stocks Analyzed:** 15
**Average Short Ratio:** 25.3%
**High Short Interest Stocks:** 3

## 🔴 High Short Interest

### GME
- Short % of Float: 45.2%
- Days to Cover: 8.5 days
- Short Ratio: 52.3%
- Risk: High (Short Squeeze Potential)

### AMC
- Short % of Float: 38.1%
- Days to Cover: 6.2 days
- Short Ratio: 48.7%
- Risk: High

## 🟡 Medium Short Interest

### TSLA
- Short % of Float: 15.3%
- Days to Cover: 3.8 days
- Short Ratio: 35.2%
- Risk: Medium

## 🟢 Low Short Interest

AAPL, MSFT, GOOGL, META, NVDA...

---
*Data provided by [Fintel.io](https://fintel.io)*
```

## API Considerations

### Rate Limits
- Check Fintel API plan for rate limits
- Implement same retry/delay logic as insider trading
- Cache short volume data (daily updates sufficient)

### Data Freshness
- Short volume: Updated daily (T+1)
- Short interest: Updated bi-monthly (settlement dates)
- Historical data: Available for trend analysis

### Attribution
- All outputs must include "Data provided by Fintel.io"
- Same requirement as insider trading feature

## Files to Create/Modify

### Create:
- [ ] `agent/short_volume.py` - Core module
- [ ] `test_short_volume.py` - Testing script
- [ ] `SHORT_VOLUME_SETUP.md` - Setup documentation

### Modify:
- [ ] `agent/main.py` - Add 3 new MCP tools
- [ ] `README.md` - Add short volume features
- [ ] `AGENTS.md` - Document tools
- [ ] `check_setup.py` - Add short volume API test (optional)

## Implementation Steps

1. ✅ Create implementation plan
2. Research Fintel API endpoints for short volume
3. Create `agent/short_volume.py` with core functions
4. Create `test_short_volume.py` for testing
5. Add MCP tools to `agent/main.py`
6. Test single ticker analysis
7. Test portfolio analysis
8. Update documentation
9. Verify integration

## Questions to Resolve

1. **API Endpoint Verification**: Need to verify exact Fintel API endpoints
   - Check API documentation for `/shortVolume/` endpoint
   - Check API documentation for `/shortInterest/` endpoint
   - Verify response format

2. **Historical Data**: How many days of historical data available?
   - Default to 30 days for analysis
   - Allow configurable lookback period

3. **Update Frequency**: How often should data be refreshed?
   - Daily for short volume
   - Bi-monthly for short interest

4. **Caching Strategy**: Should we cache short volume data?
   - Similar to Alpha Vantage price cache
   - Daily refresh should be sufficient

## ✅ API ISSUE RESOLVED!

After testing with the existing Fintel API key, we discovered the **correct endpoint**:

**Working Endpoint:**
- **Short Volume**: `https://api.fintel.io/web/v/0.0/ss/{country}/{symbol}`
- Returns daily short volume data with `marketDate`, `shortVolume`, `totalVolume`, `shortVolumeRatio`
- Provides historical data (typically 10+ days)

**Not Available:**
- Short Interest data (`/api/v1/shortInterest/`) - Returns 404
- This appears to be in a different API tier

**Solution:**
- Use `/ss/` endpoint for short volume tracking ✅
- Skip short interest metrics for now (only available in higher tier)
- Focus on daily short volume ratio analysis

## What's Available vs Not Available

### ✅ Available (Working)
- **Daily Short Volume**: via `/ss/` endpoint
  - Short volume (shares)
  - Total volume (shares)
  - Short volume ratio (%)
  - Historical data (10+ days)
  - Trend analysis capabilities

### ❌ Not Available (404 Error)
- **Short Interest Data**: % of float, days to cover
  - Would require higher API tier
  - Can be added later if API tier upgraded

## Current Implementation Scope

Based on available data, we're implementing:
1. ✅ Daily short volume tracking
2. ✅ Short volume ratio analysis
3. ✅ 7-day and 30-day trend analysis
4. ✅ Risk scoring based on short volume patterns
5. ❌ Short interest metrics (deferred - not available)

## Current Implementation Status

✅ **Completed:**
- Core module `agent/short_volume.py` with `/ss/` endpoint integration
- Testing script `test_short_volume.py` - **Working!**
- Risk analysis logic based on short volume ratios
- Portfolio analysis framework
- Tested with AAPL, TSLA, GME - **All working!**

📋 **Remaining Tasks:**
- Add MCP tools to `agent/main.py`
- Update README.md with short volume features
- Update AGENTS.md with tool documentation
- Create SHORT_VOLUME_SETUP.md

## Next Steps

1. ~~Verify Fintel API endpoints~~ ✅ DONE - Found `/ss/` endpoint
2. ~~Test API calls~~ ✅ DONE - Working perfectly
3. ~~Update implementation~~ ✅ DONE - Using `/ss/` endpoint
4. Add MCP tools and documentation
