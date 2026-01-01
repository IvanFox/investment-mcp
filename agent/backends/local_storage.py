"""
Local file-based storage backend.

Uses JSON files with atomic writes, backups, and validation.
"""

import json
import os
import shutil
from typing import Dict, List, Optional, Any
import logging

from ..storage_backend import StorageBackend

logger = logging.getLogger(__name__)

HISTORY_FILE = "portfolio_history.json"
BACKUP_FILE = "portfolio_history.json.bak"
TEMP_FILE = "portfolio_history.json.tmp"

TRANSACTIONS_FILE = "transactions.json"
TRANSACTIONS_BACKUP_FILE = "transactions.json.bak"
TRANSACTIONS_TEMP_FILE = "transactions.json.tmp"


class LocalFileBackend(StorageBackend):
    """Local JSON file storage backend with safety features."""
    
    def __init__(self, data_dir: str = "."):
        """
        Initialize local file backend.
        
        Args:
            data_dir: Directory to store files (default: current directory)
        """
        self.data_dir = data_dir
        self.backup_dir = os.path.join(data_dir, "backup")
        
        self.history_path = os.path.join(data_dir, HISTORY_FILE)
        self.backup_path = os.path.join(self.backup_dir, BACKUP_FILE)
        self.temp_path = os.path.join(data_dir, TEMP_FILE)
        
        self.transactions_path = os.path.join(data_dir, TRANSACTIONS_FILE)
        self.transactions_backup_path = os.path.join(self.backup_dir, TRANSACTIONS_BACKUP_FILE)
        self.transactions_temp_path = os.path.join(data_dir, TRANSACTIONS_TEMP_FILE)
        
        # Create data directory and backup directory if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.debug(f"LocalFileBackend initialized: {self.history_path}, backup_dir: {self.backup_dir}")
    
    def save_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """
        Save snapshot to local file with atomic write and backup.
        
        Safety features:
        - Validates snapshot structure
        - Fails fast on corrupted JSON (preserves corrupted file)
        - Creates .bak backup before overwriting
        - Uses atomic write (temp file + rename)
        - Comprehensive error logging
        
        Args:
            snapshot_data: Dictionary conforming to Snapshot JSON Schema
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Step 1: Read existing history with fail-fast on corruption
            history = []
            if os.path.exists(self.history_path):
                logger.debug(f"Reading existing history from {self.history_path}...")
                try:
                    with open(self.history_path, "r") as f:
                        content = f.read().strip()
                        if content:
                            history = json.loads(content)

                    # Validate history is a list
                    if not isinstance(history, list):
                        raise ValueError(
                            f"History file {self.history_path} has invalid format: expected list, got {type(history).__name__}"
                        )

                    logger.debug(f"Successfully loaded {len(history)} existing snapshots")

                except json.JSONDecodeError as e:
                    # FAIL FAST: Do not overwrite corrupted file
                    error_msg = (
                        f"CRITICAL: History file {self.history_path} contains invalid JSON and cannot be parsed.\n"
                        f"JSON Error: {e}\n"
                        f"The file has been preserved and will NOT be overwritten.\n"
                        f"Action required:\n"
                        f"  1. Inspect the file at: {os.path.abspath(self.history_path)}\n"
                        f"  2. Fix the JSON syntax manually, or\n"
                        f"  3. Restore from backup: {os.path.abspath(self.backup_path)} (if available), or\n"
                        f"  4. Rename/move the corrupted file and restart with fresh history"
                    )
                    logger.error(error_msg)
                    return False

                except IOError as e:
                    logger.error(f"Failed to read history file {self.history_path}: {e}")
                    return False
            else:
                logger.debug(f"No existing history file found. Starting fresh.")

            # Step 2: Create backup of existing file (if it exists)
            if os.path.exists(self.history_path):
                logger.debug(f"Creating backup: {self.history_path} -> {self.backup_path}")
                try:
                    shutil.copy2(self.history_path, self.backup_path)
                    logger.debug("Backup created successfully")
                except IOError as e:
                    logger.error(f"Failed to create backup file {self.backup_path}: {e}")
                    return False

            # Step 3: Append new snapshot
            history.append(snapshot_data)
            logger.debug(f"Appended new snapshot. Total snapshots: {len(history)}")

            # Step 4: Validate that the full history can be serialized to JSON
            try:
                json_content = json.dumps(history, indent=2, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize history to JSON: {e}")
                return False

            # Step 5: Atomic write using temp file + rename
            logger.debug(f"Writing to temporary file: {self.temp_path}")
            try:
                # Write to temp file
                with open(self.temp_path, "w") as f:
                    f.write(json_content)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk

                logger.debug(
                    f"Temp file written successfully. Renaming {self.temp_path} -> {self.history_path}"
                )

                # Atomic rename (POSIX guarantees atomicity)
                os.replace(self.temp_path, self.history_path)

                logger.info(
                    f"LocalFileBackend: Successfully saved snapshot to {self.history_path}. Total snapshots: {len(history)}"
                )
                return True

            except IOError as e:
                logger.error(f"Failed to write history file: {e}")
                # Clean up temp file if it exists
                if os.path.exists(self.temp_path):
                    try:
                        os.remove(self.temp_path)
                        logger.debug(f"Cleaned up temporary file {self.temp_path}")
                    except:
                        pass
                return False

        except Exception as e:
            logger.error(f"LocalFileBackend: Failed to save snapshot: {e}", exc_info=True)
            return False
    
    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent snapshot from the history file.
        
        Returns:
            dict: The latest snapshot object, or None if the file is empty
        """
        try:
            if not os.path.exists(self.history_path):
                logger.debug(f"History file {self.history_path} does not exist")
                return None

            with open(self.history_path, "r") as f:
                content = f.read().strip()
                if not content:
                    logger.debug("History file is empty")
                    return None

                history = json.loads(content)

                if not isinstance(history, list):
                    logger.warning("History file format invalid")
                    return None

                if len(history) == 0:
                    logger.debug("No snapshots in history")
                    return None

                latest = history[-1]
                logger.debug(
                    f"Retrieved latest snapshot from {latest.get('timestamp', 'unknown time')}"
                )
                return latest

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"LocalFileBackend: Failed to read latest snapshot: {e}")
            return None
        except Exception as e:
            logger.error(f"LocalFileBackend: Unexpected error reading latest snapshot: {e}")
            return None
    
    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        """
        Retrieve all snapshots from the history file.
        
        Returns:
            list: All snapshot objects, or empty list if file doesn't exist or is empty
        """
        try:
            if not os.path.exists(self.history_path):
                logger.debug(f"History file {self.history_path} does not exist")
                return []

            with open(self.history_path, "r") as f:
                content = f.read().strip()
                if not content:
                    logger.debug("History file is empty")
                    return []

                history = json.loads(content)

                if not isinstance(history, list):
                    logger.warning("History file format invalid")
                    return []

                logger.debug(f"Retrieved {len(history)} snapshots from history")
                return history

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"LocalFileBackend: Failed to read snapshots: {e}")
            return []
        except Exception as e:
            logger.error(f"LocalFileBackend: Unexpected error reading snapshots: {e}")
            return []
    
    def save_transactions(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Save transactions to local file with atomic write and backup.
        
        Uses same safety pattern as save_snapshot:
        - Creates .bak backup before overwriting
        - Uses atomic write (temp file + rename)
        - Comprehensive error logging
        
        Args:
            transaction_data: Full transactions object (not a list)
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Step 1: Create backup of existing file (if it exists)
            if os.path.exists(self.transactions_path):
                logger.debug(f"Creating backup: {self.transactions_path} -> {self.transactions_backup_path}")
                try:
                    shutil.copy2(self.transactions_path, self.transactions_backup_path)
                    logger.debug("Backup created successfully")
                except IOError as e:
                    logger.error(f"Failed to create backup file {self.transactions_backup_path}: {e}")
                    return False
            
            # Step 2: Validate that data can be serialized to JSON
            try:
                json_content = json.dumps(transaction_data, indent=2, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize transactions to JSON: {e}")
                return False
            
            # Step 3: Atomic write using temp file + rename
            logger.debug(f"Writing to temporary file: {self.transactions_temp_path}")
            try:
                # Write to temp file
                with open(self.transactions_temp_path, "w") as f:
                    f.write(json_content)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk
                
                logger.debug(
                    f"Temp file written successfully. Renaming {self.transactions_temp_path} -> {self.transactions_path}"
                )
                
                # Atomic rename (POSIX guarantees atomicity)
                os.replace(self.transactions_temp_path, self.transactions_path)
                
                sell_count = transaction_data.get("metadata", {}).get("sell_count", 0)
                buy_count = transaction_data.get("metadata", {}).get("buy_count", 0)
                logger.info(
                    f"LocalFileBackend: Successfully saved transactions to {self.transactions_path}. "
                    f"Sells: {sell_count}, Buys: {buy_count}"
                )
                return True
                
            except IOError as e:
                logger.error(f"Failed to write transactions file: {e}")
                # Clean up temp file if it exists
                if os.path.exists(self.transactions_temp_path):
                    try:
                        os.remove(self.transactions_temp_path)
                        logger.debug(f"Cleaned up temporary file {self.transactions_temp_path}")
                    except:
                        pass
                return False
        
        except Exception as e:
            logger.error(f"LocalFileBackend: Failed to save transactions: {e}", exc_info=True)
            return False
    
    def get_transactions(self) -> Optional[Dict[str, Any]]:
        """
        Load transactions from local file.
        
        Returns:
            dict: Transaction data or None if file doesn't exist
        """
        try:
            if not os.path.exists(self.transactions_path):
                logger.debug(f"Transactions file {self.transactions_path} does not exist")
                return None
            
            with open(self.transactions_path, "r") as f:
                content = f.read().strip()
                if not content:
                    logger.warning("Transactions file is empty")
                    return None
                
                data = json.loads(content)
                
                sell_count = data.get("metadata", {}).get("sell_count", 0)
                buy_count = data.get("metadata", {}).get("buy_count", 0)
                logger.debug(
                    f"LocalFileBackend: Loaded transactions from {self.transactions_path}. "
                    f"Sells: {sell_count}, Buys: {buy_count}"
                )
                return data
        
        except json.JSONDecodeError as e:
            logger.error(f"LocalFileBackend: Transactions file contains invalid JSON: {e}")
            return None
        except IOError as e:
            logger.error(f"LocalFileBackend: Failed to read transactions file: {e}")
            return None
        except Exception as e:
            logger.error(f"LocalFileBackend: Unexpected error reading transactions: {e}")
            return None
    
    def delete_snapshot(self, index: int) -> bool:
        """
        Delete snapshot by index from local file.
        
        Creates timestamped backup before deletion.
        Uses atomic write pattern for safety.
        
        Args:
            index: Zero-based index of snapshot to delete
            
        Returns:
            bool: True if deletion succeeded, False otherwise
        """
        try:
            # Step 1: Load current history
            if not os.path.exists(self.history_path):
                logger.error(f"LocalFileBackend: History file does not exist: {self.history_path}")
                return False
            
            with open(self.history_path, "r") as f:
                content = f.read().strip()
                if not content:
                    logger.error("LocalFileBackend: History file is empty")
                    return False
                
                history = json.loads(content)
            
            if not isinstance(history, list):
                logger.error("LocalFileBackend: History file format invalid (not a list)")
                return False
            
            # Step 2: Validate index
            if index < 0 or index >= len(history):
                logger.error(
                    f"LocalFileBackend: Index {index} out of range "
                    f"(valid: 0-{len(history)-1})"
                )
                return False
            
            # Step 3: Create timestamped backup in backup/ folder
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_filename = f"{HISTORY_FILE}.bak.{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            try:
                shutil.copy2(self.history_path, backup_path)
                logger.info(f"LocalFileBackend: Created backup at {backup_path}")
            except IOError as e:
                logger.error(f"LocalFileBackend: Failed to create backup: {e}")
                return False
            
            # Step 4: Remove snapshot at index
            deleted_snapshot = history.pop(index)
            deleted_timestamp = deleted_snapshot.get("timestamp", "unknown")
            deleted_value = deleted_snapshot.get("total_value_eur", 0.0)
            
            logger.info(
                f"LocalFileBackend: Deleting snapshot at index {index}: "
                f"{deleted_timestamp} (€{deleted_value:,.2f})"
            )
            
            # Step 5: Write updated history atomically
            try:
                json_content = json.dumps(history, indent=2, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"LocalFileBackend: Failed to serialize history: {e}")
                return False
            
            # Write to temp file
            try:
                with open(self.temp_path, "w") as f:
                    f.write(json_content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic rename
                os.replace(self.temp_path, self.history_path)
                
                logger.info(
                    f"LocalFileBackend: Successfully deleted snapshot. "
                    f"Remaining snapshots: {len(history)}"
                )
                return True
                
            except IOError as e:
                logger.error(f"LocalFileBackend: Failed to write updated history: {e}")
                # Clean up temp file if it exists
                if os.path.exists(self.temp_path):
                    try:
                        os.remove(self.temp_path)
                    except:
                        pass
                return False
        
        except json.JSONDecodeError as e:
            logger.error(f"LocalFileBackend: Invalid JSON in history file: {e}")
            return False
        except Exception as e:
            logger.error(f"LocalFileBackend: Unexpected error deleting snapshot: {e}", exc_info=True)
            return False
    
    def is_available(self) -> bool:
        """
        Check if local storage is available.
        
        Returns:
            bool: Always True (local storage is always available)
        """
        return True
