#!/usr/bin/env python3
"""
Simple script to call get_upcoming_events() with uv

Usage:
  uv run python run_events.py
"""

import sys
sys.path.insert(0, '/Users/ivan.lissitsnoi/Projects/investment-mcp')

from agent import events_tracker
from agent import sheets_connector


def main():
    print("=" * 70)
    print("📅 Portfolio Events Tracker")
    print("=" * 70)
    print()

    try:
        # Fetch portfolio data from Google Sheets
        print("Fetching portfolio data...")
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)

        print(f"Found {len(normalized_data)} assets in portfolio")
        print()

        # Get upcoming events
        print("Fetching upcoming events from Alpha Vantage...")
        result = events_tracker.get_portfolio_upcoming_events(normalized_data)

        if result.get("success"):
            print("✅ Success!\n")
            events = result.get("events", [])

            if not events:
                print("No upcoming events within 60 days")
            else:
                print(f"📅 Upcoming Events (Next 2 Months)\n")
                for event in events:
                    print(f"**{event.get('type')}**")
                    print(f"- Ticker: {event.get('ticker')}")
                    print(f"- Company: {event.get('company_name')}")
                    print(f"- Date: {event.get('date')} ({event.get('days_until')} days)")

                    if event.get("estimate"):
                        print(f"- Estimate: {event.get('estimate')}")
                    if event.get("amount"):
                        print(f"- Amount: {event.get('amount')}")
                    if event.get("payment_date"):
                        print(f"- Payment Date: {event.get('payment_date')}")
                    print()

            print(f"Summary:")
            print(f"- Total Events: {result.get('total_events')}")
            print(f"- Earnings Reports: {result.get('earnings_count')}")
            print(f"- Dividend Payouts: {result.get('dividends_count')}")
        else:
            print("❌ Error\n")
            print(f"Error: {result.get('error')}")

            if result.get("unmapped_stocks"):
                print("\n⚠️  Unmapped Stocks:")
                unmapped = result.get("unmapped_stocks", [])
                unique_stocks = []
                for msg in unmapped:
                    stock_name = msg.split("'")[1] if "'" in msg else msg
                    if stock_name not in unique_stocks:
                        unique_stocks.append(stock_name)

                for stock in unique_stocks:
                    print(f"  - {stock}")

                print(f"\n✏️  Add these to ticker_mapping.json:")
                print(f'   "mappings": {{')
                for stock in unique_stocks:
                    print(f'     "{stock}": "TICKER_HERE",')
                print(f'   }}')

            if result.get("help"):
                print(f"\nHelp: {result.get('help')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
