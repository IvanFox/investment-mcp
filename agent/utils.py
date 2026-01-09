"""
Utility functions for the Investment MCP Agent.

Contains helper functions for error handling, sanitization, and common operations.
"""

import os
import re
from typing import Union


def sanitize_error_message(error: Union[Exception, str]) -> str:
    """
    Remove sensitive information from error messages before returning to clients.

    Security: Prevents information disclosure by sanitizing file paths, usernames,
    and other system details from error messages. Full error details are still
    available in logs for debugging.

    This function:
    - Replaces home directory with ~ to hide username
    - Replaces absolute paths with PROJECT_ROOT/ placeholder
    - Preserves error type and core message for debugging

    Args:
        error: Exception object or error string to sanitize

    Returns:
        str: Sanitized error message safe to send to MCP clients

    Example:
        >>> e = ValueError("/Users/john/Projects/investment-mcp/config.yaml not found")
        >>> sanitize_error_message(e)
        'PROJECT_ROOT/config.yaml not found'

        >>> sanitize_error_message("Failed at /Users/john/Documents/data.json")
        'Failed at ~/Documents/data.json'
    """
    # Convert exception to string if needed
    if isinstance(error, Exception):
        msg = str(error)
    else:
        msg = error

    # Replace home directory with ~ (hides username)
    home_dir = os.path.expanduser("~")
    msg = msg.replace(home_dir, "~")

    # Replace absolute paths to investment-mcp project
    # Pattern matches: /path/to/investment-mcp/
    msg = re.sub(
        r"/[\w/-]+/investment-mcp/",
        "PROJECT_ROOT/",
        msg,
    )

    # Also handle Windows-style paths if present
    msg = re.sub(
        r"[A-Z]:\\[\w\\-]+\\investment-mcp\\",
        r"PROJECT_ROOT\\",  # Use raw string for backslashes
        msg,
    )

    return msg


def sanitize_path_for_logging(path: str) -> str:
    """
    Sanitize file paths for safe logging.

    Similar to sanitize_error_message but specifically for paths.
    Useful when logging file operations.

    Args:
        path: File path to sanitize

    Returns:
        str: Sanitized path safe for logging

    Example:
        >>> sanitize_path_for_logging("/Users/john/Projects/investment-mcp/config.yaml")
        'PROJECT_ROOT/config.yaml'
    """
    # Replace home directory
    home_dir = os.path.expanduser("~")
    sanitized = path.replace(home_dir, "~")

    # Replace project root
    sanitized = re.sub(
        r"/[\w/-]+/investment-mcp/",
        "PROJECT_ROOT/",
        sanitized,
    )

    return sanitized
