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
    
    @abstractmethod
    def save_transactions(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Save transactions to storage.
        
        Args:
            transaction_data: Full transactions object (not a list)
            
        Returns:
            bool: True if save successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_transactions(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve transactions from storage.
        
        Returns:
            dict: Transaction data or None if unavailable
        """
        pass
    
    @abstractmethod
    def delete_snapshot(self, index: int) -> bool:
        """
        Delete snapshot by index (0-based).
        
        Args:
            index: Zero-based index of snapshot to delete
            
        Returns:
            bool: True if deletion succeeded, False otherwise
        """
        pass
