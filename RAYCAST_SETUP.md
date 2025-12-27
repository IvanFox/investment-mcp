# Raycast Integration - Setup Complete! 🎉

## What Was Built

A complete set of 6 Raycast Script Commands for instant portfolio analytics:

1. **Portfolio Status** - Current holdings (live from spreadsheet)
2. **Quick Analysis** - Live vs snapshot comparison  
3. **Winners & Losers** - Top movers (historical)
4. **Upcoming Events** - Earnings calendar
5. **Insider Trades (Portfolio)** - All stocks
6. **Insider Trades (Ticker)** - Single stock lookup

## Architecture

**Two-Layer Design:**
- **Bash Wrappers** (`raycast-scripts/portfolio-status`, etc.)
  - Executable by Raycast
  - Set up environment and working directory
  - Call Python implementations via `uv run python3`

- **Python Implementations** (`raycast-scripts/lib/*_impl.py`)
  - Actual business logic
  - Easy to test and maintain
  - Standard Python code with type hints

## Installation

### 1. Verify Setup
```bash
cd /Users/ivan.lissitsnoi/Projects/investment-mcp
./test_raycast_integration.sh
```

You should see:
```
✅ All tests passed!
```

### 2. Add to Raycast

1. Open Raycast Settings (`Cmd+,`)
2. Navigate to **Extensions → Script Commands**
3. Click **Add Directory**
4. Select: `/Users/ivan.lissitsnoi/Projects/investment-mcp/raycast-scripts/`
5. Click **Add**

### 3. Verify in Raycast

1. Open Raycast (`Cmd+Space`)
2. Type "Portfolio"
3. You should see all 6 commands listed

## Usage

### From Raycast

Open Raycast (`Cmd+Space`) and type the command name:
- `Portfolio Status` - See all holdings
- `Quick Analysis` - Recent changes
- `Winners & Losers` - Top movers
- `Upcoming Events` - Earnings dates
- `Insider Trades (Portfolio)` - All stocks
- `Insider Trades (Ticker)` - Enter ticker when prompted

### From Terminal (for testing)

```bash
# From any directory
/Users/ivan.lissitsnoi/Projects/investment-mcp/raycast-scripts/portfolio-status

# With pretty formatting
/Users/ivan.lissitsnoi/Projects/investment-mcp/raycast-scripts/quick-analysis | jq
```

## How It Works

1. **User invokes command in Raycast**
2. **Raycast executes bash wrapper** (e.g., `portfolio-status`)
3. **Wrapper changes to project directory** and runs:
   ```bash
   uv run python3 lib/portfolio-status_impl.py
   ```
4. **Python implementation:**
   - Imports agent modules
   - Calls appropriate function (e.g., `get_portfolio_status_json()`)
   - Returns JSON output
5. **Raycast displays the JSON** in fullOutput mode

## Troubleshooting

### Scripts Don't Appear in Raycast

**Check:**
1. Directory is added in Raycast settings
2. Scripts are executable: `ls -la raycast-scripts/portfolio-status`
3. Restart Raycast

### "Exec Format Error"

This has been fixed! The new bash wrapper approach eliminates this error.

**If you still see it:**
1. Check shebang: `head -1 raycast-scripts/portfolio-status`
   - Should be: `#!/bin/bash`
2. Verify wrapper is executable: `chmod +x raycast-scripts/*`

### "Config Not Found" Error

The bash wrapper sets the correct working directory automatically.

**If you still see it:**
1. Verify config.yaml exists: `ls -la config.yaml`
2. Check from terminal: `./raycast-scripts/portfolio-status`

### Script Runs But Shows Error

Check the actual error in the JSON output - it will include troubleshooting hints.

**Common issues:**
- Google Sheets credentials not configured
- API keys missing (Alpha Vantage, Fintel)
- Ticker mappings incomplete

## Files Created

```
raycast-scripts/
├── portfolio-status                      # Bash wrapper
├── quick-analysis                        # Bash wrapper
├── portfolio-winners-losers              # Bash wrapper
├── upcoming-events                       # Bash wrapper
├── insider-trades-portfolio              # Bash wrapper
├── insider-trades-ticker                 # Bash wrapper (with argument)
├── README.md                             # Comprehensive documentation
└── lib/
    ├── raycast_client.py                 # Agent client
    ├── json_formatter.py                 # JSON formatting
    ├── error_handler.py                  # Error handling
    ├── portfolio-status_impl.py          # Python implementation
    ├── quick-analysis_impl.py            # Python implementation
    ├── portfolio-winners-losers_impl.py  # Python implementation
    ├── upcoming-events_impl.py           # Python implementation
    ├── insider-trades-portfolio_impl.py  # Python implementation
    └── insider-trades-ticker_impl.py     # Python implementation

agent/
└── raycast_tools.py                      # JSON-focused agent functions

test_raycast_integration.sh               # Integration tests
```

## What's Different From Original Plan

**Original Approach (Had Issues):**
- Python scripts with `.py` extension
- Shebang pointing to `.python-wrapper` bash script
- **Problem:** Kernel doesn't support chained shebangs → Exec format error

**Current Approach (Working):**
- Bash wrapper scripts (no extension)
- Python implementations in `lib/*_impl.py`
- **Benefit:** Clean, reliable, works perfectly with Raycast

## Testing

Run the integration test:
```bash
./test_raycast_integration.sh
```

This verifies:
- ✅ Agent modules import correctly
- ✅ JSON structure is valid
- ✅ All scripts are executable
- ✅ Raycast metadata is present
- ✅ Scripts work from different directories

## Next Steps

1. **Use from Raycast** - Open Raycast and try the commands!
2. **Customize** - Edit `lib/*_impl.py` files to adjust behavior
3. **Extend** - Add new scripts following the same pattern

## Support

- **General help:** See `raycast-scripts/README.md`
- **Testing:** Run `./test_raycast_integration.sh`
- **Configuration:** Check `config.yaml` and keychain credentials

---

**Enjoy your Raycast-powered portfolio analytics!** 📊💼⚡
