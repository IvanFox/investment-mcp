"""
Google Cloud Storage backend for portfolio history.

Uses GCS bucket to store portfolio_history.json for cross-machine sync.
"""

import json
from typing import Dict, List, Optional, Any
import logging

from google.cloud import storage
from google.api_core import exceptions as gcp_exceptions

from ..storage_backend import StorageBackend

logger = logging.getLogger(__name__)

BLOB_NAME = "portfolio_history.json"


class GCPStorageBackend(StorageBackend):
    """Google Cloud Storage backend."""
    
    def __init__(self, bucket_name: str, credentials_dict: Dict[str, Any]):
        """
        Initialize GCP storage backend.
        
        Args:
            bucket_name: GCS bucket name (e.g., "investment_snapshots")
            credentials_dict: Service account credentials dictionary
        """
        self.bucket_name = bucket_name
        self.blob_name = BLOB_NAME
        
        try:
            from google.oauth2 import service_account
            
            # Create credentials from dictionary
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict
            )
            
            # Initialize GCS client
            self.client = storage.Client(credentials=credentials)
            self.bucket = self.client.bucket(bucket_name)
            
            logger.info(f"GCPStorageBackend initialized for bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCP storage: {e}")
            raise
    
    def save_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """
        Save snapshot to GCS.
        
        Strategy:
        1. Download current history from GCS
        2. Append new snapshot
        3. Upload updated history
        4. Use atomic uploads
        
        Args:
            snapshot_data: Snapshot dictionary
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Step 1: Get current history
            history = self._download_history()
            
            # Step 2: Append new snapshot
            history.append(snapshot_data)
            
            # Step 3: Validate serialization
            json_content = json.dumps(history, indent=2, ensure_ascii=False)
            
            # Step 4: Upload with atomic write
            blob = self.bucket.blob(self.blob_name)
            blob.upload_from_string(
                json_content,
                content_type="application/json",
                if_generation_match=None  # Allow overwrites
            )
            
            logger.info(f"GCPStorageBackend: Snapshot saved to gs://{self.bucket_name}/{self.blob_name} ({len(history)} total)")
            return True
            
        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"GCPStorageBackend: GCP API error saving snapshot: {e}")
            return False
        except Exception as e:
            logger.error(f"GCPStorageBackend: Failed to save snapshot to GCS: {e}")
            return False
    
    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get latest snapshot from GCS.
        
        Returns:
            dict: Latest snapshot or None if unavailable
        """
        try:
            history = self._download_history()
            
            if not history:
                return None
            
            latest = history[-1]
            logger.debug(f"GCPStorageBackend: Retrieved latest snapshot from {latest.get('timestamp', 'unknown')}")
            return latest
            
        except Exception as e:
            logger.error(f"GCPStorageBackend: Failed to get latest snapshot from GCS: {e}")
            return None
    
    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        """
        Get all snapshots from GCS.
        
        Returns:
            list: All snapshots or empty list
        """
        try:
            history = self._download_history()
            logger.debug(f"GCPStorageBackend: Retrieved {len(history)} snapshots from GCS")
            return history
        except Exception as e:
            logger.error(f"GCPStorageBackend: Failed to get all snapshots from GCS: {e}")
            return []
    
    def is_available(self) -> bool:
        """
        Check if GCS is available.
        
        Returns:
            bool: True if GCS is reachable
        """
        try:
            # Try to check if bucket exists (lightweight operation)
            self.bucket.exists()
            return True
        except Exception as e:
            logger.warning(f"GCPStorageBackend: GCS unavailable: {e}")
            return False
    
    def delete_all_snapshots(self) -> bool:
        """
        Delete all snapshots from GCS by removing the portfolio_history.json file.
        
        ⚠️  WARNING: This is intended for TEST USE ONLY.
        This operation is irreversible and will delete all portfolio history.
        
        Returns:
            bool: True if deletion succeeded or file didn't exist, False on error
        """
        try:
            blob = self.bucket.blob(self.blob_name)
            
            if not blob.exists():
                logger.info(f"GCPStorageBackend: No data to delete (bucket empty)")
                return True
            
            blob.delete()
            logger.info(f"GCPStorageBackend: Deleted all snapshots from gs://{self.bucket_name}/{self.blob_name}")
            return True
            
        except gcp_exceptions.NotFound:
            # File already doesn't exist
            logger.debug("GCPStorageBackend: Blob not found (already deleted)")
            return True
        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"GCPStorageBackend: GCP API error deleting snapshots: {e}")
            return False
        except Exception as e:
            logger.error(f"GCPStorageBackend: Failed to delete snapshots from GCS: {e}")
            return False
    
    def _download_history(self) -> List[Dict[str, Any]]:
        """
        Download history from GCS.
        
        Returns:
            list: History array or empty list if file doesn't exist
            
        Raises:
            Exception: If download fails for reasons other than file not found
        """
        try:
            blob = self.bucket.blob(self.blob_name)
            
            if not blob.exists():
                logger.debug("No history file in GCS yet (first run)")
                return []
            
            content = blob.download_as_text()
            
            if not content.strip():
                logger.debug("History file in GCS is empty")
                return []
            
            history = json.loads(content)
            
            if not isinstance(history, list):
                logger.error("History file in GCS has invalid format (not a list)")
                return []
            
            logger.debug(f"Downloaded {len(history)} snapshots from GCS")
            return history
            
        except gcp_exceptions.NotFound:
            logger.debug("History file not found in GCS (first run)")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in GCS history file: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to download history from GCS: {e}")
            raise
