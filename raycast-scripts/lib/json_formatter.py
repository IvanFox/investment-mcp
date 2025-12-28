"""
JSON output formatting for Raycast scripts.

Provides standardized JSON response structure for all Raycast commands.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional


def format_success_response(
    data: Any, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a successful response with standard structure.

    Args:
        data: Response data (any JSON-serializable type)
        metadata: Optional metadata (timestamp added automatically)

    Returns:
        Standardized success response dictionary
    """
    response = {
        "success": True,
        "data": data,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **(metadata or {}),
        },
    }
    return response


def format_error_response(error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Format an error response with standard structure.

    Args:
        error: Main error message
        details: Optional detailed error information

    Returns:
        Standardized error response dictionary
    """
    response = {
        "success": False,
        "error": error,
        "metadata": {"timestamp": datetime.utcnow().isoformat() + "Z"},
    }

    if details:
        response["details"] = details

    return response


def print_json_response(response: Dict[str, Any]) -> None:
    """
    Print JSON response to stdout with proper formatting.

    Args:
        response: Response dictionary to print
    """
    print(json.dumps(response, indent=2, ensure_ascii=False))


def print_success(data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Print a successful response and exit.

    Args:
        data: Response data
        metadata: Optional metadata
    """
    response = format_success_response(data, metadata)
    print_json_response(response)
    sys.exit(0)


def print_error(error: str, details: Optional[str] = None, exit_code: int = 1) -> None:
    """
    Print an error response and exit.

    Args:
        error: Main error message
        details: Optional detailed error information
        exit_code: Exit code (default: 1)
    """
    response = format_error_response(error, details)
    print_json_response(response)
    sys.exit(exit_code)
