# Quick Start: Earnings Events Tracker

## 1️⃣ Setup Alpha Vantage API Key

Run the setup script:
```bash
./setup_alpha_vantage.sh
```

Then enter your Alpha Vantage API key when prompted.

**Manual alternative:**
```bash
security add-generic-password \
  -a "mcp-portfolio-agent" \
  -s "alpha-vantage-api-key" \
  -w "YOUR_API_KEY_HERE" \
  -U
```

## 2️⃣ Configure Stock Ticker Mappings

Edit `ticker_mapping.json` and add your stocks:

```json
{
  "mappings": {
    "Wise": "WISE.L",
    "Intel Corp": "INTC",
    "Apple Inc": "AAPL",
    "Microsoft Corporation": "MSFT",
    "ASML Holding": "ASML"
  }
}
```

**Tips:**
- Use exact stock names as they appear in your portfolio
- For European stocks, add exchange suffix: `.L` (London), `.PA` (Paris), `.AS` (Amsterdam)
- For US stocks, use standard ticker without suffix

## 3️⃣ Get Upcoming Events

Call the tool:
```
get_upcoming_events()
```

## 📋 What You'll See

```
📅 Upcoming Earnings Reports (Next 2 Months)

**Earnings Report**
- Ticker: AAPL
- Company: Apple Inc
- Date: 2025-11-15 (27 days)
- Estimate: 1.25

**Earnings Report**
- Ticker: MSFT
- Company: Microsoft Corporation
- Date: 2025-11-10 (22 days)
- Estimate: 3.45

Summary:
- Total Reports: 5
- Earnings Reports: 5
```

## ⚠️ Troubleshooting

### ❌ "API key not found"
→ Run `./setup_alpha_vantage.sh` to configure your key

### ❌ "Stock 'X' is not mapped"
→ Add the stock to `ticker_mapping.json`

### ❌ "No events found"
Possible reasons:
- Stocks not covered by Alpha Vantage
- No events scheduled in next 60 days
- European stock needs proper suffix (e.g., `.L`)

### ❌ "Rate limit reached"
→ Alpha Vantage has free tier limits. Wait a moment and retry.

## 📊 Features

✅ Upcoming earnings reports within 60 days (2 months)  
✅ Chronologically sorted  
✅ Earnings estimates included  
✅ Easy error messages with clear actions  
✅ Secure API key storage  
✅ Support for US and European stocks  

## 🔧 Advanced

Change the event window by editing `agent/events_tracker.py`:
```python
DAYS_THRESHOLD = 60  # Change to 90 for 3 months, etc.
```
