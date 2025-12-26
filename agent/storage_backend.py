"""
Storage backend abstraction for portfolio history.

Supports multiple backends: local files, GCP Cloud Storage, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """
        Save a snapshot to storage.
        
        Args:
            snapshot_data: Snapshot dictionary
            
        Returns:
            bool: True if save successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent snapshot.
        
        Returns:
            dict: Latest snapshot or None if unavailable
        """
        pass
    
    @abstractmethod
    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        """
        Retrieve all snapshots.
        
        Returns:
            list: All snapshots or empty list
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if backend is currently available.
        
        Returns:
            bool: True if backend is reachable
        """
        pass
