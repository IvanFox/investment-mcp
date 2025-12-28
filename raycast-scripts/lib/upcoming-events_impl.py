#!/usr/bin/env python3
"""
Upcoming Events - Raycast Script Implementation

Fetches upcoming earnings reports for portfolio stocks.
"""

from raycast_client import RaycastClient
from json_formatter import print_success, print_error
from error_handler import handle_errors, validate_config


@handle_errors
def main():
    """Main entry point for upcoming events script."""
    validate_config()

    client = RaycastClient()
    result = client.get_upcoming_events()

    # Check if result indicates failure
    if not result.get("success", True):
        error_msg = result.get("error", "Unknown error")
        details = None

        # Include unmapped stocks in details if present
        if "unmapped_stocks" in result:
            details = "\n".join(result["unmapped_stocks"])
            if "action" in result:
                details += "\n\n" + result["action"]

        print_error(error_msg, details)

    print_success(result)


if __name__ == "__main__":
    main()
