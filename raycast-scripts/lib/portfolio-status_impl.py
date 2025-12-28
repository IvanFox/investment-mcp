#!/usr/bin/env python3
"""
Portfolio Status - Raycast Script Implementation

Fetches current portfolio positions from latest snapshot.
"""

from raycast_client import RaycastClient
from json_formatter import print_success, print_error
from error_handler import handle_errors, validate_config


@handle_errors
def main():
    """Main entry point for portfolio status script."""
    validate_config()

    client = RaycastClient()
    result = client.get_portfolio_status()

    # Check if there was an error
    if "error" in result:
        print_error(result["error"], result.get("message"))

    print_success(result)


if __name__ == "__main__":
    main()
