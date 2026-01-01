"""
Hybrid storage backend with fallback support.

Uses GCP as primary, local file as fallback for offline scenarios.
Automatically retries failed GCP uploads when connectivity is restored.
"""

from typing import Dict, List, Optional, Any
import logging

from ..storage_backend import StorageBackend

logger = logging.getLogger(__name__)


class HybridStorageBackend(StorageBackend):
    """
    Hybrid storage with primary and fallback backends.
    
    Strategy:
    - Attempts primary (GCP) first
    - Falls back to secondary (local file) if primary unavailable
    - Dual-write when both available for redundancy
    - Queues retry for failed primary writes
    """
    
    def __init__(self, primary: StorageBackend, fallback: StorageBackend):
        """
        Initialize hybrid backend.
        
        Args:
            primary: Primary storage backend (e.g., GCP)
            fallback: Fallback storage backend (e.g., local file)
        """
        self.primary = primary
        self.fallback = fallback
        self.pending_sync: List[Dict[str, Any]] = []  # Queue for failed primary writes
        
        logger.info("HybridStorageBackend initialized with primary and fallback")
    
    def save_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """
        Save snapshot to storage with fallback.
        
        Strategy:
        1. Retry any pending syncs first
        2. Try primary (GCP)
        3. Always write to fallback (local) as backup
        4. If primary fails, queue for retry
        
        Args:
            snapshot_data: Snapshot dictionary
            
        Returns:
            bool: True if at least one backend succeeded
        """
        primary_success = False
        fallback_success = False
        
        # Retry any pending syncs first
        self._retry_pending_syncs()
        
        # Try primary storage
        if self.primary.is_available():
            primary_success = self.primary.save_snapshot(snapshot_data)
            if primary_success:
                logger.info("HybridStorageBackend: Snapshot saved to primary storage (GCP)")
            else:
                logger.warning("HybridStorageBackend: Primary storage write failed, queuing for retry")
                self.pending_sync.append(snapshot_data)
        else:
            logger.warning("HybridStorageBackend: Primary storage unavailable, using fallback only")
            self.pending_sync.append(snapshot_data)
        
        # Always write to fallback as backup
        fallback_success = self.fallback.save_snapshot(snapshot_data)
        if fallback_success:
            logger.info("HybridStorageBackend: Snapshot saved to fallback storage (local)")
        else:
            logger.error("HybridStorageBackend: CRITICAL: Fallback storage write failed!")
        
        # Success if at least one backend succeeded
        success = primary_success or fallback_success
        
        if not success:
            logger.error("HybridStorageBackend: Both primary and fallback storage failed!")
        
        return success
    
    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get latest snapshot, preferring primary.
        
        Returns:
            Latest snapshot from primary, or fallback if primary unavailable
        """
        # Try primary first
        if self.primary.is_available():
            snapshot = self.primary.get_latest_snapshot()
            if snapshot:
                logger.debug("HybridStorageBackend: Retrieved latest snapshot from primary")
                return snapshot
            logger.debug("HybridStorageBackend: No snapshot in primary, trying fallback")
        else:
            logger.debug("HybridStorageBackend: Primary unavailable, using fallback")
        
        # Fall back to local
        snapshot = self.fallback.get_latest_snapshot()
        if snapshot:
            logger.debug("HybridStorageBackend: Retrieved latest snapshot from fallback")
        return snapshot
    
    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        """
        Get all snapshots, preferring primary.
        
        Returns:
            All snapshots from primary, or fallback if primary unavailable
        """
        # Try primary first
        if self.primary.is_available():
            snapshots = self.primary.get_all_snapshots()
            if snapshots:
                logger.debug(f"HybridStorageBackend: Retrieved {len(snapshots)} snapshots from primary")
                return snapshots
            logger.debug("HybridStorageBackend: No snapshots in primary, trying fallback")
        else:
            logger.debug("HybridStorageBackend: Primary unavailable, using fallback")
        
        # Fall back to local
        snapshots = self.fallback.get_all_snapshots()
        logger.debug(f"HybridStorageBackend: Retrieved {len(snapshots)} snapshots from fallback")
        return snapshots
    
    def is_available(self) -> bool:
        """
        Hybrid storage is available if either backend is available.
        
        Returns:
            bool: True if at least one backend is available
        """
        return self.primary.is_available() or self.fallback.is_available()
    
    def save_transactions(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Save transactions to both primary and fallback storage.
        
        Strategy:
        1. Try primary (GCP)
        2. Always save to fallback (local)
        3. Track pending syncs if primary fails
        
        Args:
            transaction_data: Full transactions object
            
        Returns:
            bool: True if at least one backend succeeded
        """
        primary_success = False
        fallback_success = False
        
        # Try primary storage
        if self.primary.is_available():
            try:
                primary_success = self.primary.save_transactions(transaction_data)
                if primary_success:
                    logger.debug("HybridStorageBackend: Transactions saved to primary storage (GCP)")
                else:
                    logger.warning("HybridStorageBackend: Primary storage failed to save transactions")
            except Exception as e:
                logger.warning(f"HybridStorageBackend: Primary backend failed to save transactions: {e}")
        else:
            logger.debug("HybridStorageBackend: Primary storage unavailable for transactions")
        
        # Always save to fallback
        try:
            fallback_success = self.fallback.save_transactions(transaction_data)
            if fallback_success:
                logger.debug("HybridStorageBackend: Transactions saved to fallback storage (local)")
            else:
                logger.error("HybridStorageBackend: Fallback storage failed to save transactions")
        except Exception as e:
            logger.error(f"HybridStorageBackend: Fallback backend failed to save transactions: {e}")
        
        # Track sync status
        if fallback_success and not primary_success:
            # Note: We don't queue transaction retries like snapshots
            # Transactions will be re-saved on next change detection
            logger.info("HybridStorageBackend: Transactions saved to fallback only")
        
        return primary_success or fallback_success
    
    def get_transactions(self) -> Optional[Dict[str, Any]]:
        """
        Get transactions, preferring primary.
        
        Returns:
            dict: Transaction data from primary, or fallback if primary unavailable
        """
        # Try primary first
        if self.primary.is_available():
            try:
                data = self.primary.get_transactions()
                if data:
                    logger.debug("HybridStorageBackend: Loaded transactions from primary storage")
                    return data
                logger.debug("HybridStorageBackend: No transactions in primary, trying fallback")
            except Exception as e:
                logger.warning(f"HybridStorageBackend: Primary backend failed to load transactions: {e}")
        else:
            logger.debug("HybridStorageBackend: Primary unavailable, using fallback for transactions")
        
        # Fall back to local
        try:
            data = self.fallback.get_transactions()
            if data:
                logger.debug("HybridStorageBackend: Loaded transactions from fallback storage")
            return data
        except Exception as e:
            logger.error(f"HybridStorageBackend: Fallback backend failed to load transactions: {e}")
            return None
    
    def _retry_pending_syncs(self):
        """Retry any pending syncs to primary storage."""
        if not self.pending_sync:
            return
        
        if not self.primary.is_available():
            logger.debug(f"HybridStorageBackend: {len(self.pending_sync)} pending syncs waiting for primary availability")
            return
        
        logger.info(f"HybridStorageBackend: Retrying {len(self.pending_sync)} pending syncs to primary storage")
        
        retry_queue = self.pending_sync.copy()
        self.pending_sync = []
        
        for snapshot in retry_queue:
            success = self.primary.save_snapshot(snapshot)
            if success:
                logger.info("HybridStorageBackend: Pending sync succeeded")
            else:
                logger.warning("HybridStorageBackend: Pending sync failed, re-queuing")
                self.pending_sync.append(snapshot)
        
        if len(self.pending_sync) == 0:
            logger.info("HybridStorageBackend: All pending syncs completed successfully")
        else:
            logger.warning(f"HybridStorageBackend: {len(self.pending_sync)} pending syncs still queued")
    
    def delete_snapshot(self, index: int) -> bool:
        """
        Delete snapshot from both primary and fallback storage.
        
        Strategy (as per requirement):
        1. Attempt deletion from primary (GCP) first
        2. Then attempt deletion from fallback (local)
        3. Return True if either succeeds
        
        Args:
            index: Zero-based index of snapshot to delete
            
        Returns:
            bool: True if at least one backend succeeded
        """
        primary_success = False
        fallback_success = False
        
        # Step 1: Try primary (GCP) first
        if self.primary.is_available():
            try:
                primary_success = self.primary.delete_snapshot(index)
                if primary_success:
                    logger.info("HybridStorageBackend: Snapshot deleted from primary (GCP)")
                else:
                    logger.warning("HybridStorageBackend: Primary deletion failed")
            except Exception as e:
                logger.warning(f"HybridStorageBackend: Primary backend error during deletion: {e}")
        else:
            logger.warning("HybridStorageBackend: Primary unavailable, skipping")
        
        # Step 2: Try fallback (local)
        try:
            fallback_success = self.fallback.delete_snapshot(index)
            if fallback_success:
                logger.info("HybridStorageBackend: Snapshot deleted from fallback (local)")
            else:
                logger.warning("HybridStorageBackend: Fallback deletion failed")
        except Exception as e:
            logger.error(f"HybridStorageBackend: Fallback backend error during deletion: {e}")
        
        # Success if at least one backend succeeded
        overall_success = primary_success or fallback_success
        
        if overall_success:
            logger.info(
                f"HybridStorageBackend: Deletion complete "
                f"(primary: {primary_success}, fallback: {fallback_success})"
            )
        else:
            logger.error("HybridStorageBackend: Both primary and fallback deletions failed!")
        
        return overall_success
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get sync status information.
        
        Returns:
            dict: Sync status with pending count and availability
        """
        return {
            "primary_available": self.primary.is_available(),
            "fallback_available": self.fallback.is_available(),
            "pending_syncs": len(self.pending_sync),
            "fully_synced": len(self.pending_sync) == 0 and self.primary.is_available()
        }
