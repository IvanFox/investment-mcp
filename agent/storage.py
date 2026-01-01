"""
Data Persistence Layer

This module provides the public interface for portfolio history storage,
using pluggable backends (local files, GCP, etc.).
"""

import json
import logging
import subprocess
from typing import Dict, List, Optional, Any

from . import config
from .storage_backend import StorageBackend
from .backends.local_storage import LocalFileBackend
from .backends.gcp_storage import GCPStorageBackend
from .backends.hybrid_storage import HybridStorageBackend

logger = logging.getLogger(__name__)

# Global storage backend instance
_storage_backend: Optional[StorageBackend] = None


def _get_storage_backend() -> StorageBackend:
    """
    Get or initialize the storage backend.
    
    Lazy initialization on first use. Uses hybrid storage with:
    - Primary: GCP Cloud Storage
    - Fallback: Local file storage
    
    Returns:
        StorageBackend: Configured storage backend
    """
    global _storage_backend
    
    if _storage_backend is None:
        # Initialize backends
        try:
            # Local fallback backend (always initialize)
            local_backend = LocalFileBackend(data_dir=".")
            logger.info("Local file backend initialized")
            
            # Try to initialize GCP backend
            try:
                credentials_dict = _load_gcp_credentials()
                cfg = config.get_config()
                gcp_backend = GCPStorageBackend(
                    bucket_name=cfg.storage.gcp.bucket_name,
                    credentials_dict=credentials_dict
                )
                
                # Use hybrid with GCP primary + local fallback
                _storage_backend = HybridStorageBackend(
                    primary=gcp_backend,
                    fallback=local_backend
                )
                logger.info("Storage initialized: GCP primary + local fallback")
                
            except Exception as e:
                # If GCP fails to initialize, use local only
                logger.warning(f"GCP storage unavailable, using local only: {e}")
                _storage_backend = local_backend
        
        except Exception as e:
            logger.error(f"Failed to initialize storage backend: {e}")
            raise
    
    return _storage_backend


def _load_gcp_credentials() -> Dict[str, Any]:
    """
    Load GCP credentials from macOS Keychain.
    
    Returns:
        dict: Service account credentials dictionary
    """
    try:
        # Retrieve from Keychain (same account as Google Sheets)
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-a", "mcp-portfolio-agent",
                "-s", "google-sheets-credentials",
                "-w"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        hex_data = result.stdout.strip()
        
        # Decode from hex
        json_bytes = bytes.fromhex(hex_data)
        json_str = json_bytes.decode('utf-8')
        
        credentials = json.loads(json_str)
        
        logger.info("GCP credentials loaded from Keychain")
        return credentials
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to retrieve credentials from Keychain: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to parse credentials: {e}")
        raise


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
    Save a portfolio snapshot to storage.
    
    Validates snapshot structure and saves to configured backend
    (GCP primary with local fallback).
    
    Args:
        snapshot_data: Dictionary conforming to Snapshot JSON Schema
        
    Raises:
        ValueError: If snapshot data is invalid
        IOError: If all storage backends fail
    """
    try:
        # Validate input
        logger.info("Validating snapshot data structure...")
        _validate_snapshot_structure(snapshot_data)
        
        # Get backend
        backend = _get_storage_backend()
        
        # Save snapshot
        logger.info("Saving snapshot to storage...")
        success = backend.save_snapshot(snapshot_data)
        
        if not success:
            raise IOError("All storage backends failed to save snapshot")
        
        logger.info("Snapshot saved successfully")
        
        # Log sync status if using hybrid storage
        if isinstance(backend, HybridStorageBackend):
            status = backend.get_sync_status()
            if not status["fully_synced"]:
                logger.warning(
                    f"Snapshot saved locally, {status['pending_syncs']} pending GCP syncs"
                )
        
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}", exc_info=True)
        raise


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent snapshot from storage.
    
    Returns:
        dict: The latest snapshot object, or None if unavailable
    """
    try:
        backend = _get_storage_backend()
        snapshot = backend.get_latest_snapshot()
        
        if snapshot:
            logger.info(f"Retrieved latest snapshot from {snapshot.get('timestamp', 'unknown time')}")
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Failed to get latest snapshot: {e}")
        return None


def get_all_snapshots() -> List[Dict[str, Any]]:
    """
    Retrieves all snapshots from storage.
    
    Returns:
        list: All snapshot objects, or empty list if unavailable
    """
    try:
        backend = _get_storage_backend()
        snapshots = backend.get_all_snapshots()
        
        logger.info(f"Retrieved {len(snapshots)} snapshots from storage")
        return snapshots
        
    except Exception as e:
        logger.error(f"Failed to get all snapshots: {e}")
        return []


def get_storage_status() -> Dict[str, Any]:
    """
    Get current storage backend status.
    
    Returns:
        dict: Storage status information
    """
    try:
        backend = _get_storage_backend()
        
        status = {
            "backend_type": backend.__class__.__name__,
            "available": backend.is_available()
        }
        
        # Add hybrid-specific status
        if isinstance(backend, HybridStorageBackend):
            status.update(backend.get_sync_status())
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get storage status: {e}")
        return {"error": str(e)}


def save_transactions(
    sell_transactions: List[Dict[str, Any]],
    buy_transactions: List[Dict[str, Any]],
    currency_rates: Dict[str, float]
) -> bool:
    """
    Save transactions to storage if changed.
    
    Public API wrapper - delegates to transaction_storage module.
    
    Args:
        sell_transactions: List of sell transaction dicts
        buy_transactions: List of buy transaction dicts
        currency_rates: Currency conversion rates used
    
    Returns:
        bool: True if transactions were saved (changed), False if unchanged
    """
    from . import transaction_storage as txn_storage
    
    try:
        return txn_storage.save_transactions(
            sell_transactions=sell_transactions,
            buy_transactions=buy_transactions,
            currency_rates=currency_rates
        )
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}", exc_info=True)
        raise


def get_transactions() -> Dict[str, Any]:
    """
    Get current transactions from storage.
    
    Returns:
        dict: Transaction data with sell_transactions, buy_transactions, metadata
              Returns empty structure if no transactions exist
    """
    from . import transaction_storage as txn_storage
    
    try:
        return txn_storage.get_transactions()
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}", exc_info=True)
        return {
            "sell_transactions": [],
            "buy_transactions": [],
            "metadata": {}
        }


def list_snapshots() -> List[Dict[str, Any]]:
    """
    List all snapshots with index and timestamp.
    
    Returns:
        list: List of snapshot summaries with:
            - index: 1-based index for user display
            - timestamp: ISO timestamp string
            - total_value_eur: Portfolio total value
            - asset_count: Number of assets
    """
    try:
        backend = _get_storage_backend()
        all_snapshots = backend.get_all_snapshots()
        
        if not all_snapshots:
            logger.info("No snapshots found")
            return []
        
        # Build summary list with 1-based indices
        summaries = []
        for i, snapshot in enumerate(all_snapshots):
            summaries.append({
                "index": i + 1,  # 1-based for user display
                "timestamp": snapshot.get("timestamp", "Unknown"),
                "total_value_eur": snapshot.get("total_value_eur", 0.0),
                "asset_count": len(snapshot.get("assets", []))
            })
        
        logger.info(f"Listed {len(summaries)} snapshots")
        return summaries
        
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}", exc_info=True)
        return []


def delete_snapshot(index: int, confirm: bool = False) -> Dict[str, Any]:
    """
    Delete a specific snapshot from portfolio history.
    
    Args:
        index: 1-based index of snapshot to delete (as shown in list_snapshots)
        confirm: Must be True to execute deletion (safety check)
    
    Returns:
        dict: {
            "success": bool,
            "deleted_snapshot": dict (if found),
            "error": str (if failed),
            "remaining_count": int
        }
    """
    try:
        # Safety check
        if not confirm:
            return {
                "success": False,
                "error": "Deletion cancelled. Set confirm=True to proceed.",
                "warning": "This operation is permanent and will delete the snapshot from both GCP and local storage."
            }
        
        # Validate index (must be positive)
        if index < 1:
            return {
                "success": False,
                "error": f"Invalid index: {index}. Index must be >= 1."
            }
        
        # Get current snapshots to validate and get info
        backend = _get_storage_backend()
        all_snapshots = backend.get_all_snapshots()
        
        if not all_snapshots:
            return {
                "success": False,
                "error": "No snapshots found in history."
            }
        
        # Convert 1-based to 0-based
        zero_based_index = index - 1
        
        if zero_based_index >= len(all_snapshots):
            return {
                "success": False,
                "error": f"Index {index} out of range. Valid range: 1-{len(all_snapshots)}"
            }
        
        # Get snapshot info before deletion
        deleted_snapshot = all_snapshots[zero_based_index]
        
        # Perform deletion
        logger.info(f"Deleting snapshot at index {index} (0-based: {zero_based_index})")
        success = backend.delete_snapshot(zero_based_index)
        
        if success:
            remaining = len(all_snapshots) - 1
            logger.info(f"Snapshot deleted successfully. Remaining: {remaining}")
            return {
                "success": True,
                "deleted_snapshot": {
                    "index": index,
                    "timestamp": deleted_snapshot.get("timestamp", "Unknown"),
                    "total_value_eur": deleted_snapshot.get("total_value_eur", 0.0),
                    "asset_count": len(deleted_snapshot.get("assets", []))
                },
                "remaining_count": remaining
            }
        else:
            return {
                "success": False,
                "error": "Deletion failed. Check logs for details."
            }
        
    except Exception as e:
        logger.error(f"Failed to delete snapshot: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
