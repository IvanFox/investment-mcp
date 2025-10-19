# Using `uv` to Call get_upcoming_events()

There are multiple ways to call `get_upcoming_events()` using `uv`:

## Method 1: Using the run_events.py Script (Recommended)

The simplest way to run the tool:

```bash
uv run python run_events.py
```

This is the recommended approach because:
- Clean output formatting
- Handles errors gracefully
- Shows helpful suggestions for missing mappings
- Easy to integrate into workflows

### Example Output
```
======================================================================
📅 Portfolio Events Tracker
======================================================================

Fetching portfolio data...
Found 30 assets in portfolio

Fetching upcoming events from Alpha Vantage...
✅ Success!

📅 Upcoming Events (Next 2 Months)

**Earnings Report**
- Ticker: AAPL
- Company: Apple Inc
- Date: 2025-11-15 (27 days)
- Estimate: 1.25

**Dividend Payout**
- Ticker: MSFT
- Company: Microsoft Corporation
- Date: 2025-11-10 (22 days)
- Amount: 0.68
- Payment Date: 2025-12-05

Summary:
- Total Events: 8
- Earnings Reports: 5
- Dividend Payouts: 3
```

## Method 2: Direct Python with uv

Run inline Python code:

```bash
uv run python3 -c "
import sys
sys.path.insert(0, '.')
from agent import events_tracker, sheets_connector

raw_data = sheets_connector.fetch_portfolio_data()
normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
result = events_tracker.get_portfolio_upcoming_events(normalized_data)

if result.get('success'):
    print(f'Found {result.get(\"total_events\")} upcoming events')
else:
    print(f'Error: {result.get(\"error\")}')
"
```

## Method 3: Interactive Python Shell with uv

```bash
uv run python3
```

Then in the Python shell:

```python
import sys
sys.path.insert(0, '.')

from agent import events_tracker, sheets_connector

# Fetch portfolio
raw_data = sheets_connector.fetch_portfolio_data()
normalized_data = sheets_connector.parse_and_normalize_data(raw_data)

# Get events
result = events_tracker.get_portfolio_upcoming_events(normalized_data)

# Print results
if result.get('success'):
    for event in result.get('events', []):
        print(f"{event['type']}: {event['ticker']} on {event['date']}")
else:
    print(f"Error: {result['error']}")
```

## Method 4: Using uv with FastMCP Server

Start the server:

```bash
uv run python server.py
```

Then in another terminal, use the MCP client to call the tool.

## Prerequisites

Before running any method, ensure:

### 1. API Key Configured

Store your Alpha Vantage API key:

```bash
./setup_alpha_vantage.sh
```

Or manually:

```bash
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "alpha-vantage-api-key" \
  -w "YOUR_API_KEY" \
  -U
```

### 2. Stock Mappings Updated

Edit `ticker_mapping.json` and ensure all your portfolio stocks are mapped:

```json
{
  "mappings": {
    "Apple Inc": "AAPL",
    "Microsoft Corporation": "MSFT",
    "Wise": "WISE.L",
    "ASML": "ASML.AS"
  }
}
```

## Troubleshooting

### "API key not found"
→ Run `./setup_alpha_vantage.sh` and enter your API key

### "Stock 'X' is not mapped"
→ Add the stock to `ticker_mapping.json` in the "mappings" section

### "Failed to fetch events from Alpha Vantage"
→ Check your API key is valid
→ Check your internet connection
→ Check Alpha Vantage rate limits (5 calls/min free tier)

## Running via uv.lock

All dependencies are locked in `uv.lock`. To ensure reproducible runs:

```bash
# Install locked dependencies
uv sync

# Run the script
uv run python run_events.py
```

## Integration Examples

### In a Cron Job

```bash
0 9 * * 1 cd /path/to/investment-mcp && uv run python run_events.py >> /var/log/portfolio_events.log
```

### In a GitHub Action

```yaml
- name: Check Portfolio Events
  run: |
    uv run python run_events.py
```

### In a Python Script

```python
import subprocess
import json

result = subprocess.run(
    ["uv", "run", "python", "run_events.py"],
    cwd="/path/to/investment-mcp",
    capture_output=True,
    text=True
)

print(result.stdout)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
```

## Performance Notes

- First run with `uv`: May take 2-3 seconds to initialize
- Subsequent runs: ~2-5 seconds depending on API response time
- API calls: 2 per invocation (earnings + dividends)
- Rate limit: 5 calls/min on free Alpha Vantage tier

## Summary

| Method | Command | Best For |
|--------|---------|----------|
| Script | `uv run python run_events.py` | Regular usage, automation |
| Inline | `uv run python3 -c "..."` | Quick tests, CI/CD |
| Shell | `uv run python3` | Interactive debugging |
| Server | `uv run python server.py` | MCP client integration |
