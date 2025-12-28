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
