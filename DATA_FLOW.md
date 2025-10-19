# Data Flow: Earnings Events Tracker

## Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER CALLS: get_upcoming_events()                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ agent/main.py → get_upcoming_events() MCP Tool                              │
│                                                                              │
│ 1. Fetch portfolio from Google Sheets                                       │
│    sheets_connector.fetch_portfolio_data()                                  │
│                                    │                                        │
│                                    ▼                                        │
│ 2. Parse and normalize asset data                                           │
│    sheets_connector.parse_and_normalize_data()                              │
│    Returns: [{name, quantity, purchase_price, current_value, category}]    │
│                                    │                                        │
│                                    ▼                                        │
│ 3. Get upcoming events                                                      │
│    events_tracker.get_portfolio_upcoming_events(normalized_data)            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ agent/events_tracker.py → get_portfolio_upcoming_events()                   │
│                                                                              │
│ 1. Load and validate ticker mappings                                        │
│    load_ticker_mapping() from ticker_mapping.json                           │
│    Check each asset has a mapping                                           │
│                                    │                                        │
│                                    ▼                                        │
│    If any unmapped: RETURN ERROR                                            │
│    {"success": False, "unmapped_stocks": [...], "action": "..."}            │
│                                    │ (if OK)                                │
│                                    ▼                                        │
│ 2. Load API Key                                                             │
│    load_alpha_vantage_api_key()                                             │
│    From macOS Keychain                                                      │
│                                    │                                        │
│                                    ▼                                        │
│    If not found: RETURN ERROR                                               │
│    {"success": False, "error": "API Key Error: ...", "help": "..."}         │
│                                    │ (if OK)                                │
│                                    ▼                                        │
│ 3. Fetch Events from Alpha Vantage                                          │
│    ┌─────────────────────────────────────────────────────┐                 │
│    │ fetch_earnings_calendar(api_key)                    │                 │
│    │ EARNINGS_CALENDAR endpoint                          │                 │
│    │ Returns: [{symbol, reportDate, estimate, ...}]     │                 │
│    └─────────────────────────────────────────────────────┘                 │
│                                    │                                        │
│                                    ▼                                        │
│ 4. Filter Events (60-day window)                                            │
│    filter_upcoming_events(earnings, "reportDate")                      │
│                                    │                                        │
│    For each event:                                                          │
│    - Parse date                                                             │
│    - Check if within 60 days from today                                     │
│    - Calculate days_until                                                   │
│    - Keep only matching events                                              │
│                                    │                                        │
│                                    ▼                                        │
│ 5. Sort Chronologically                                                     │
│    sort_events_chronologically(all_events)                                  │
│                                    │                                        │
│    Order by: event_date ASC (earliest first)                                │
│                                    │                                        │
│                                    ▼                                        │
│ 6. Match to Portfolio                                                       │
│    Filter events to only those in portfolio tickers                         │
│                                    │                                        │
│                                    ▼                                        │
│ 7. Format Results                                                           │
│    {                                                                        │
│      "success": True,                                                       │
│      "events": [                                                            │
│        {                                                                    │
│          "type": "Earnings Report",                                         │
│          "ticker": "AAPL",                                                  │
│          "company_name": "Apple Inc",                                       │
│          "date": "2025-11-15",                                              │
│          "days_until": 27,                                                  │
│          "report_date": "2025-11-15",                                       │
│          "estimate": "1.25"                                                 │
│        },                                                                   │
│        ...                                                                  │
│      ],                                                                     │
│      "total_events": 5,                                                     │
│      "earnings_count": 5,                                                   │
│      "as_of": "2025-10-23T15:30:45.123456+00:00"                            │
│    }                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ agent/main.py → Format and Return                                           │
│                                                                              │
│ Convert structured result to user-friendly markdown:                        │
│                                                                              │
│ 📅 Upcoming Earnings Reports (Next 2 Months)                                 │
│                                                                              │
│ **Earnings Report**                                                         │
│ - Ticker: AAPL                                                              │
│ - Company: Apple Inc                                                        │
│ - Date: 2025-11-15 (27 days)                                                │
│ - Estimate: 1.25                                                            │
│                                                                              │
│ **Earnings Report**                                                         │
│ - Ticker: MSFT                                                              │
│ - Company: Microsoft Corporation                                            │
│ - Date: 2025-11-10 (22 days)                                                │
│ - Estimate: 3.45                                                            │
│                                                                              │
│ Summary:                                                                    │
│ - Total Reports: 5                                                          │
│ - Earnings Reports: 5                                                       │
│ - Last Updated: 2025-10-23T15:30:45.123456+00:00                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER RECEIVES: Formatted earnings report list                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Error Flow

### Error: Missing API Key
```
get_upcoming_events()
    │
    ▼
load_alpha_vantage_api_key()
    │
    ├─ Keychain lookup fails
    │
    ▼
RETURN: {
  "success": False,
  "error": "Alpha Vantage API Key Error: Failed to retrieve...",
  "help": "Please store your Alpha Vantage API key in keychain..."
}
    │
    ▼
Format error message with setup instructions
```

### Error: Unmapped Stocks
```
get_upcoming_events()
    │
    ▼
get_ticker_for_asset("Stock Name")
    │
    ├─ "Stock Name" not in ticker_mapping.json
    │
    ▼
Collect all unmapped stocks
    │
    ▼
RETURN: {
  "success": False,
  "error": "Unmapped stocks found",
  "unmapped_stocks": [
    "Stock 'XYZ' is not mapped in ticker_mapping.json...",
    "Stock 'ABC' is not mapped in ticker_mapping.json..."
  ],
  "action": "Please update ticker_mapping.json with the missing stock mappings"
}
    │
    ▼
Format error message with list of missing mappings
```

### Error: API Failure
```
get_upcoming_events()
    │
    ▼
fetch_earnings_calendar(api_key)
    │
    ├─ Network timeout or API error
    │
    ▼
RETURN: {
  "success": False,
  "error": "Failed to fetch events from Alpha Vantage: [error details]"
}
    │
    ▼
Format error message
```

## Data Transformations

### Portfolio Asset → Ticker
```
Input: {name: "Apple Inc", quantity: 10, ...}
       ↓
       lookup: ticker_mapping.json
       ↓
Output: "AAPL"
```

### Raw API Event → Filtered Earnings Event
```
Input: {
  symbol: "AAPL",
  reportDate: "2025-11-15",
  estimate: "1.25"
}
       ↓
       1. Parse date
       2. Check if within 60 days
       3. Calculate days_until
       4. Match ticker to company name
       ↓
Output: {
  type: "Earnings Report",
  ticker: "AAPL",
  company_name: "Apple Inc",
  date: "2025-11-15",
  days_until: 27,
  report_date: "2025-11-15",
  estimate: "1.25"
}
```

### Sorted Events → Markdown
```
Input: [
  {date: "2025-11-10", days: 22, ...},
  {date: "2025-11-15", days: 27, ...},
  {date: "2025-11-08", days: 20, ...}
]
       ↓
       1. Sort by date
       2. Format each event
       3. Add summary stats
       ↓
Output: "📅 Upcoming Earnings Reports (Next 2 Months)
         **Earnings Report**
         - Date: 2025-11-08 (20 days)
         ...
         Summary: Total Reports: 3"
```
