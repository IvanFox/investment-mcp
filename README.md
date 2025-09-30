# Investment MCP Agent

An automated portfolio monitoring and performance analysis system built with FastMCP that tracks your complete investment portfolio including stocks, bonds, ETFs, pension, and cash positions.

## 🔐 Security & Credentials

**This system uses macOS Keychain for secure credential storage. You must configure your Google Cloud Service Account credentials in Keychain before using the system.**

### Required Setup: Store Credentials in Keychain

Before running the agent, you need to store your Google Cloud Service Account JSON credentials in macOS Keychain:

```bash
# Store your service account JSON in Keychain
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat your-service-account.json | xxd -p | tr -d '\n')" \
  -T ""
```

**Important**: 
- Replace `your-service-account.json` with the path to your actual service account file
- The credentials are stored as hex-encoded JSON for security
- Never commit service account files to version control

## Overview

This MCP agent provides comprehensive portfolio monitoring across all major asset classes:

- **Stocks** (US & EU markets with multi-currency support)
- **Bonds** (Corporate and government bonds)  
- **ETFs** (Index funds and diversified investments)
- **Pension** (2nd and 3rd pillar schemes)
- **Cash** (Multi-currency positions)

The system automatically fetches data from Google Sheets, performs currency conversions, and generates detailed performance reports with portfolio allocation breakdowns.

## Features

- **Complete Portfolio Tracking**: 6 asset categories across 29+ positions
- **Automated Data Fetching**: Real-time Google Sheets integration
- **Multi-Currency Support**: USD, EUR, GBP with live conversion rates
- **Performance Analysis**: Week-over-week comparison with gain/loss tracking
- **Rich Reporting**: Markdown reports with portfolio allocation charts
- **Security**: Keychain-secured credential storage
- **MCP Integration**: Three FastMCP tools for portfolio management

## Setup

1. **Configure Google Cloud Service Account credentials in Keychain (Required)**
2. Configure your sheet details in `sheet-details.json`
3. Install dependencies: `uv sync`
4. Run the agent to start monitoring

### Keychain Credential Setup

```bash
# Store your service account JSON in macOS Keychain
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat path/to/your-service-account.json | xxd -p | tr -d '\n')" \
  -T ""
```

### Automated Keychain Setup

For easier setup, use the provided script:

```bash
# Make the script executable
chmod +x setup_keychain.sh

# Run the automated setup
./setup_keychain.sh path/to/your-service-account.json
```

This script will:
- Validate your service account JSON
- Store it securely in Keychain (hex-encoded)
- Remove the original file for security
- Test the keychain integration
- Display next steps

## Usage

The agent provides several tools:

- `run_portfolio_analysis()`: Manually trigger a portfolio analysis
- `get_portfolio_status()`: Get current portfolio status
- `get_portfolio_history_summary()`: View historical performance summary

## Technical Stack

- **Language**: Python 3.12+
- **Framework**: FastMCP
- **APIs**: Google Sheets API
- **Storage**: JSON file persistence
- **Package Manager**: uv