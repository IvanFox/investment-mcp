"""
Error handling for Raycast scripts.

Provides consistent error handling and user-friendly error messages.
"""

import sys
import traceback
from typing import Callable, Any
from json_formatter import print_error


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in Raycast scripts.

    Catches all exceptions and formats them as JSON error responses.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            print_error(
                "Configuration file not found",
                f"Please ensure config.yaml exists in the project root. Details: {str(e)}",
            )
        except PermissionError as e:
            print_error(
                "Permission denied",
                f"Cannot access required file or resource. Details: {str(e)}",
            )
        except ValueError as e:
            print_error("Invalid data or configuration", str(e))
        except KeyError as e:
            print_error("Missing required data", f"Expected key not found: {str(e)}")
        except Exception as e:
            # For unexpected errors, include full traceback in details
            tb = traceback.format_exc()
            print_error(
                f"Unexpected error: {type(e).__name__}", f"{str(e)}\n\nTraceback:\n{tb}"
            )

    return wrapper


def validate_config() -> None:
    """
    Validate that required configuration exists.

    Raises:
        FileNotFoundError: If config.yaml is missing
        ValueError: If configuration is invalid
    """
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}\n"
            "Please create config.yaml from config.yaml.example"
        )
