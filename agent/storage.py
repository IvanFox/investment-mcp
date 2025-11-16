"""
Data Persistence in JSON

This module handles all file I/O for portfolio_history.json.
"""

import json
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

HISTORY_FILE = "portfolio_history.json"
BACKUP_FILE = "portfolio_history.json.bak"
TEMP_FILE = "portfolio_history.json.tmp"


def _validate_snapshot_structure(snapshot_data: Dict[str, Any]) -> None:
    """
    Validates that snapshot data has the required structure.

    Args:
        snapshot_data: Dictionary to validate

    Raises:
        ValueError: If snapshot structure is invalid
    """
    required_fields = ["timestamp", "total_value_eur", "assets"]

    for field in required_fields:
        if field not in snapshot_data:
            raise ValueError(f"Invalid snapshot: missing required field '{field}'")

    if not isinstance(snapshot_data["assets"], list):
        raise ValueError("Invalid snapshot: 'assets' must be a list")

    if not isinstance(snapshot_data["total_value_eur"], (int, float)):
        raise ValueError("Invalid snapshot: 'total_value_eur' must be a number")


def save_snapshot(snapshot_data: Dict[str, Any]) -> None:
    """
    Appends a new snapshot to the portfolio_history.json file with data protection.

    Safety features:
    - Validates snapshot structure before writing
    - Fails fast on corrupted JSON (preserves corrupted file for recovery)
    - Creates .bak backup before overwriting
    - Uses atomic write (temp file + rename) to prevent partial writes
    - Comprehensive error logging

    Args:
        snapshot_data: Dictionary conforming to the Snapshot JSON Schema

    Raises:
        ValueError: If snapshot data is invalid
        IOError: If file operations fail
        json.JSONDecodeError: If existing file contains invalid JSON
    """
    try:
        # Step 1: Validate input data structure
        logger.info("Validating snapshot data structure...")
        _validate_snapshot_structure(snapshot_data)

        # Step 2: Read existing history with fail-fast on corruption
        history = []
        if os.path.exists(HISTORY_FILE):
            logger.info(f"Reading existing history from {HISTORY_FILE}...")
            try:
                with open(HISTORY_FILE, "r") as f:
                    content = f.read().strip()
                    if content:
                        history = json.loads(content)

                # Validate history is a list
                if not isinstance(history, list):
                    raise ValueError(
                        f"History file {HISTORY_FILE} has invalid format: expected list, got {type(history).__name__}"
                    )

                logger.info(f"Successfully loaded {len(history)} existing snapshots")

            except json.JSONDecodeError as e:
                # FAIL FAST: Do not overwrite corrupted file
                error_msg = (
                    f"CRITICAL: History file {HISTORY_FILE} contains invalid JSON and cannot be parsed.\n"
                    f"JSON Error: {e}\n"
                    f"The file has been preserved and will NOT be overwritten.\n"
                    f"Action required:\n"
                    f"  1. Inspect the file at: {os.path.abspath(HISTORY_FILE)}\n"
                    f"  2. Fix the JSON syntax manually, or\n"
                    f"  3. Restore from backup: {os.path.abspath(BACKUP_FILE)} (if available), or\n"
                    f"  4. Rename/move the corrupted file and restart with fresh history"
                )
                logger.error(error_msg)
                raise json.JSONDecodeError(
                    f"Corrupted history file preserved at {os.path.abspath(HISTORY_FILE)}: {e.msg}",
                    e.doc,
                    e.pos,
                ) from e

            except IOError as e:
                error_msg = f"Failed to read history file {HISTORY_FILE}: {e}"
                logger.error(error_msg)
                raise IOError(error_msg) from e
        else:
            logger.info(f"No existing history file found. Starting fresh.")

        # Step 3: Create backup of existing file (if it exists)
        if os.path.exists(HISTORY_FILE):
            logger.info(f"Creating backup: {HISTORY_FILE} -> {BACKUP_FILE}")
            try:
                shutil.copy2(HISTORY_FILE, BACKUP_FILE)
                logger.info("Backup created successfully")
            except IOError as e:
                error_msg = f"Failed to create backup file {BACKUP_FILE}: {e}"
                logger.error(error_msg)
                raise IOError(error_msg) from e

        # Step 4: Append new snapshot
        history.append(snapshot_data)
        logger.info(f"Appended new snapshot. Total snapshots: {len(history)}")

        # Step 5: Validate that the full history can be serialized to JSON
        try:
            json_content = json.dumps(history, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            error_msg = f"Failed to serialize history to JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        # Step 6: Atomic write using temp file + rename
        logger.info(f"Writing to temporary file: {TEMP_FILE}")
        try:
            # Write to temp file
            with open(TEMP_FILE, "w") as f:
                f.write(json_content)
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force OS to write to disk

            logger.info(
                f"Temp file written successfully. Renaming {TEMP_FILE} -> {HISTORY_FILE}"
            )

            # Atomic rename (POSIX guarantees atomicity)
            os.replace(TEMP_FILE, HISTORY_FILE)

            logger.info(
                f"Successfully saved snapshot to {HISTORY_FILE}. Total snapshots: {len(history)}"
            )

        except IOError as e:
            error_msg = f"Failed to write history file: {e}"
            logger.error(error_msg)
            # Clean up temp file if it exists
            if os.path.exists(TEMP_FILE):
                try:
                    os.remove(TEMP_FILE)
                    logger.info(f"Cleaned up temporary file {TEMP_FILE}")
                except:
                    pass
            raise IOError(error_msg) from e

    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}", exc_info=True)
        raise


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent snapshot from the history file.

    Returns:
        dict: The latest snapshot object, or None if the file is empty
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"History file {HISTORY_FILE} does not exist")
            return None

        with open(HISTORY_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                logger.info("History file is empty")
                return None

            history = json.loads(content)

            if not isinstance(history, list):
                logger.warning("History file format invalid")
                return None

            if len(history) == 0:
                logger.info("No snapshots in history")
                return None

            latest = history[-1]
            logger.info(
                f"Retrieved latest snapshot from {latest.get('timestamp', 'unknown time')}"
            )
            return latest

    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read latest snapshot: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading latest snapshot: {e}")
        return None


def get_all_snapshots() -> List[Dict[str, Any]]:
    """
    Retrieves all snapshots from the history file.

    Returns:
        list: All snapshot objects, or empty list if file doesn't exist or is empty
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"History file {HISTORY_FILE} does not exist")
            return []

        with open(HISTORY_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                logger.info("History file is empty")
                return []

            history = json.loads(content)

            if not isinstance(history, list):
                logger.warning("History file format invalid")
                return []

            logger.info(f"Retrieved {len(history)} snapshots from history")
            return history

    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read snapshots: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading snapshots: {e}")
        return []
