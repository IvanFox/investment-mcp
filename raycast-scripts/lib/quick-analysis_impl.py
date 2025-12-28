#!/usr/bin/env python3
"""
Quick Analysis - Raycast Script Implementation

Compares current portfolio state (from spreadsheet) vs last snapshot.
"""

from raycast_client import RaycastClient
from json_formatter import print_success, print_error
from error_handler import handle_errors, validate_config


@handle_errors
def main():
    """Main entry point for quick analysis script."""
    validate_config()

    client = RaycastClient()
    result = client.get_quick_analysis()

    # Check if there was an error
    if "error" in result:
        print_error(result["error"], result.get("message"))

    print_success(result)


if __name__ == "__main__":
    main()
