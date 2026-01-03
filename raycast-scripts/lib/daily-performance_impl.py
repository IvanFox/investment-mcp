#!/usr/bin/env python3
"""
Daily Performance - Raycast Script Implementation

Shows top 5 stock winners and losers based on daily change percentage.
"""

from raycast_client import RaycastClient
from json_formatter import print_success, print_error
from error_handler import handle_errors, validate_config


@handle_errors
def main():
    """Main entry point for daily performance script."""
    validate_config()

    client = RaycastClient()
    result = client.get_daily_performance()

    # Check if there was an error
    if "error" in result:
        print_error(result["error"], result.get("message"))

    print_success(result)


if __name__ == "__main__":
    main()
