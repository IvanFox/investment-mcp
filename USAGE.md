# Investment MCP Agent - Usage Guide

## Quick Start

The Investment MCP Agent has been successfully implemented and **uses macOS Keychain for secure credential storage**.

### 🔐 Current Authentication Status

✅ **Keychain Integration**: Credentials loaded from macOS Keychain  
✅ **Service Account Configured**: Uses secure Service Account authentication  
⏳ **Setup Required**: Store Service Account JSON in Keychain (one-time setup)

### 1. Keychain Credential Setup (Required)

**Store your Google Cloud Service Account credentials in Keychain:**

```bash
# Replace 'your-service-account.json' with your actual file path
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat your-service-account.json | xxd -p | tr -d '\n')" \
  -T ""
```

**Verify the setup:**
```bash
# This should return your hex-encoded credentials
security find-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w
```

### 2. Share Google Sheet with Service Account

After storing credentials in Keychain, share your Google Sheet with the service account email found in your JSON file (typically something like `investment-mcp@your-project.iam.gserviceaccount.com`).

### 3. Test the Setup

```bash
# Run the setup verification script
uv run python check_setup.py

# Or run a direct portfolio analysis
uv run python -m agent.main
```

### 3. Running the Agent

#### Option A: As an MCP Server (Recommended)
```bash
uv run python server.py
```

This starts the FastMCP server with these tools:
- `run_portfolio_analysis()` - Trigger portfolio analysis
- `get_portfolio_status()` - Get current portfolio status
- `get_portfolio_history_summary()` - View historical performance

#### Option B: Direct Analysis
```bash
uv run python -m agent.main
```

### 4. Google Sheets Configuration

Your Google Sheet should be structured as follows:

- **Sheet Name**: `2025` (configurable in `agent/sheets_connector.py`)
- **Currency Rates**: 
  - Cell O2: GBP/EUR rate
  - Cell O3: USD/EUR rate
- **Asset Ranges**:
  - A5:L19 - US Stocks
  - A20:L35 - EU Stocks
  - A37:L39 - Bonds
  - A40:L45 - ETFs
- **Pension Data**:
  - A52:E53 - Pension schemes (2nd and 3rd pillar)
- **Cash Positions**:
  - A58:B60 - Cash in different currencies

Each asset row should contain:
- Column A: Asset Name
- Column B: Quantity
- Column C: Category/Other data (not used by system)
- Column D: Purchase Price per Unit (with currency symbol: $, €, £)
- Column E: Current Price per Unit (with currency symbol: $, €, £)

**Pension Data Structure**:
- Column A: Pension scheme name (e.g., "II level", "III level")
- Column E: Current pension value (with currency symbol: €)

**Cash Data Structure**:
- Column A: Currency name (e.g., "USD", "EUR", "GBP")
- Column B: Cash amount (numeric value)

**Note**: The system automatically:
- Detects currency from symbols ($, €, £) in columns D and E
- Converts all prices to EUR using live exchange rates
- Calculates total amounts by multiplying price × quantity
- Tracks pension and cash positions as separate asset categories

### 5. System Features

✅ **Implemented Features**:
- **Secure Service Account authentication**
- Google Sheets API integration
- **Complete asset tracking**: Stocks, Bonds, ETFs, Pension (2nd/3rd pillar), Cash positions
- Multi-currency support (USD, EUR, GBP) with automatic conversion
- Portfolio snapshot creation with complete asset breakdown
- Week-over-week comparison across all asset types
- Top/bottom movers analysis
- New/sold positions tracking
- Realized gains/losses calculation
- **Portfolio allocation breakdown** by asset category (6 categories)
- Rich Markdown reports with emojis and clear sections
- JSON-based persistent storage
- FastMCP server integration
- Comprehensive error handling
- Logging throughout

### 6. Sample Output

The system generates detailed weekly reports like:

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

**Total Realized P&L:** 💔 €-500.00

---

## 📊 Portfolio Allocation
- **EU Stocks**: €195,097.56 (48.1%)
- **Pension**: €93,000.00 (22.9%)
- **US Stocks**: €40,478.60 (10.0%)
- **Cash**: €35,850.45 (8.8%)
- **ETFs**: €34,236.95 (8.4%)
- **Bonds**: €6,640.00 (1.6%)
```

### 7. Data Storage

- **File**: `portfolio_history.json`
- **Format**: Array of timestamped snapshots
- **Retention**: All historical data (no automatic cleanup)

### 8. Security & Authentication

🔐 **Service Account Benefits**:
- More secure than API keys
- No need to make sheets public
- Granular permission control
- Audit trail of access
- Revocable access

### 9. Troubleshooting

**Common Issues**:

1. **Keychain Access Denied**: Ensure the credentials are properly stored in Keychain
   ```bash
   # Verify credentials exist in keychain
   security find-generic-password \
     -a "mcp-portfolio-agent" \
     -s "google-sheets-credentials" \
     -w
   ```

2. **Permission Denied**: Ensure your sheet is shared with the service account email
   - Find your service account email in the keychain credentials
   - Share the Google Sheet with this email (Viewer permission)

3. **Sheet Not Found**: Verify `sheetId` in `sheet-details.json`

4. **Empty Data**: Check sheet ranges in `sheets_connector.py`

**Debug Mode**:
```bash
# Test keychain credential access
security find-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w

# Run setup verification
uv run python check_setup.py

# Enable debug logging
export LOG_LEVEL=DEBUG
uv run python -m agent.main
```

**Keychain Setup Command** (if credentials missing):
```bash
# Store service account JSON in keychain
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat your-service-account.json | xxd -p | tr -d '\n')" \
  -T ""
```

### 10. Security & Credentials

🔐 **Keychain Integration**:
- Service Account credentials stored securely in macOS Keychain
- No plain-text credential files in the repository
- Hex-encoded storage for additional security
- Automatic credential retrieval during runtime

**Security Benefits**:
- Credentials never stored in plain text files
- No risk of accidental credential commits to version control
- Leverages macOS security infrastructure
- Granular permission control via Service Account
- Audit trail of access
- Revocable access

### 11. Next Steps

The system is fully functional and ready for production use:

✅ **Complete**: All implementation phases finished  
✅ **Secure**: Service Account authentication configured  
⏳ **Pending**: Share sheet with service account (1-minute setup)  
🚀 **Ready**: For automated weekly portfolio monitoring  

## Architecture Overview

The implementation follows the exact plan specifications with enhanced security:

- ✅ **Phase 1**: Project structure created
- ✅ **Phase 2**: Google Sheets connector with Service Account auth
- ✅ **Phase 3**: Analysis and snapshot logic completed
- ✅ **Phase 4**: JSON persistence implemented
- ✅ **Phase 5**: Reporting and FastMCP integration done
- ✅ **Bonus**: Service Account security upgrade

All modules are modular, well-documented, and production-ready.