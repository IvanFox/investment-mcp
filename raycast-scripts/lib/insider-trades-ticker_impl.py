#!/usr/bin/env python3
"""
Insider Trades (Ticker) - Raycast Script Implementation

Fetches insider trading data for a specific ticker.
"""

import sys
from raycast_client import RaycastClient
from json_formatter import print_success, print_error
from error_handler import handle_errors, validate_config


@handle_errors
def main():
    """Main entry point for ticker insider trades script."""
    validate_config()

    # Get ticker from command line argument
    if len(sys.argv) < 2:
        print_error(
            "Missing ticker argument",
            "Usage: insider-trades-ticker TICKER\nExample: insider-trades-ticker AAPL",
        )

    ticker = sys.argv[1].strip().upper()

    if not ticker:
        print_error("Invalid ticker", "Ticker cannot be empty")

    client = RaycastClient()
    result = client.get_ticker_insider_trades(ticker)

    # Check if result indicates failure
    if not result.get("success", True):
        error_msg = result.get("error", "Unknown error")
        details = result.get("details")
        print_error(error_msg, details)

    print_success(result)


if __name__ == "__main__":
    main()
