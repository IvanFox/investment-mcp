"""
Transaction Storage Module

Handles persistence of buy and sell transactions separately from portfolio snapshots.
Implements hash-based change detection to minimize unnecessary writes.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def _normalize_transaction_for_hashing(txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize transaction dict for consistent hashing.
    
    Normalizations:
    - Strip timezone from dates (assume UTC)
    - Round floats to 4 decimal places
    - Extract only essential fields
    - Consistent field ordering
    
    Args:
        txn: Transaction dictionary
    
    Returns:
        dict: Normalized transaction for hashing
    """
    # Determine which price field to use
    price_eur = txn.get("sell_price_per_unit_eur") or txn.get("purchase_price_per_unit_eur", 0.0)
    
    return {
        "date": str(txn["date"])[:19],  # Strip timezone for consistency
        "asset_name": str(txn["asset_name"]),
        "quantity": round(float(txn["quantity"]), 4),
        "currency": str(txn["currency"]),
        "price_eur": round(float(price_eur), 4)
    }


def compute_transaction_hash(transactions: List[Dict[str, Any]]) -> str:
    """
    Compute SHA-256 hash of transaction list for change detection.
    
    Normalizes transaction data before hashing:
    - Sorts transactions by date, then asset_name
    - Rounds floats to 4 decimal places
    - Excludes timezone info from dates (UTC assumed)
    
    Args:
        transactions: List of transaction dicts
    
    Returns:
        str: SHA-256 hash as hex string with 'sha256:' prefix
    """
    if not transactions:
        return "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # Hash of empty list
    
    # Normalize all transactions
    normalized = [_normalize_transaction_for_hashing(txn) for txn in transactions]
    
    # Sort by date, then asset name for consistent ordering
    normalized.sort(key=lambda x: (x["date"], x["asset_name"]))
    
    # Compute hash
    json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    
    return f"sha256:{hash_obj.hexdigest()}"


def _validate_transaction_structure(data: Dict[str, Any]) -> None:
    """
    Validate transactions.json structure.
    
    Args:
        data: Transaction data dictionary
        
    Raises:
        ValueError: If structure is invalid
    """
    required_fields = ["last_updated", "sell_transactions", "buy_transactions", "metadata"]
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Invalid transaction data: missing required field '{field}'")
    
    if not isinstance(data["sell_transactions"], list):
        raise ValueError("Invalid transaction data: 'sell_transactions' must be a list")
    
    if not isinstance(data["buy_transactions"], list):
        raise ValueError("Invalid transaction data: 'buy_transactions' must be a list")
    
    if not isinstance(data["metadata"], dict):
        raise ValueError("Invalid transaction data: 'metadata' must be a dict")


def get_transactions() -> Dict[str, Any]:
    """
    Load transactions from storage.
    
    Returns:
        dict: Transaction data with keys:
            - sell_transactions: List[Dict]
            - buy_transactions: List[Dict]
            - metadata: Dict (includes hashes, last_updated, etc.)
        
        Returns empty structure if file doesn't exist.
    """
    from .storage import _get_storage_backend
    
    try:
        backend = _get_storage_backend()
        data = backend.get_transactions()
        
        if data is None:
            # No transactions file exists yet
            logger.info("No transactions file found, returning empty structure")
            return {
                "sell_transactions": [],
                "buy_transactions": [],
                "metadata": {}
            }
        
        # Validate structure
        _validate_transaction_structure(data)
        
        sell_count = len(data.get("sell_transactions", []))
        buy_count = len(data.get("buy_transactions", []))
        logger.info(f"Loaded transactions: {sell_count} sells, {buy_count} buys")
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}", exc_info=True)
        # Return empty structure on error
        return {
            "sell_transactions": [],
            "buy_transactions": [],
            "metadata": {}
        }


def transactions_have_changed(
    sell_transactions: List[Dict[str, Any]],
    buy_transactions: List[Dict[str, Any]]
) -> Dict[str, bool]:
    """
    Check if transactions have changed compared to stored versions.
    
    Args:
        sell_transactions: Current sell transactions from Sheets
        buy_transactions: Current buy transactions from Sheets
    
    Returns:
        dict: {
            "sell_changed": bool,
            "buy_changed": bool,
            "any_changed": bool
        }
    """
    # Get stored transactions
    stored_data = get_transactions()
    stored_metadata = stored_data.get("metadata", {})
    
    # Compute current hashes
    current_sell_hash = compute_transaction_hash(sell_transactions)
    current_buy_hash = compute_transaction_hash(buy_transactions)
    
    # Get stored hashes (if they exist)
    stored_sell_hash = stored_metadata.get("sell_hash", "")
    stored_buy_hash = stored_metadata.get("buy_hash", "")
    
    # Compare
    sell_changed = current_sell_hash != stored_sell_hash
    buy_changed = current_buy_hash != stored_buy_hash
    
    logger.debug(
        f"Transaction change detection: "
        f"sell_changed={sell_changed}, buy_changed={buy_changed}"
    )
    
    return {
        "sell_changed": sell_changed,
        "buy_changed": buy_changed,
        "any_changed": sell_changed or buy_changed
    }


def save_transactions(
    sell_transactions: List[Dict[str, Any]],
    buy_transactions: List[Dict[str, Any]],
    currency_rates: Dict[str, float]
) -> bool:
    """
    Save transactions to storage if they have changed.
    
    Computes hashes for buy and sell transactions separately.
    Only saves if hashes differ from stored versions.
    
    Args:
        sell_transactions: List of parsed sell transactions
        buy_transactions: List of parsed buy transactions
        currency_rates: Exchange rates used for conversion
    
    Returns:
        bool: True if transactions were saved (changed), False if unchanged
    """
    from .storage import _get_storage_backend
    
    try:
        # Check if transactions have changed
        change_status = transactions_have_changed(sell_transactions, buy_transactions)
        
        if not change_status["any_changed"]:
            logger.info("Transactions unchanged, skipping save")
            return False
        
        # Compute hashes
        sell_hash = compute_transaction_hash(sell_transactions)
        buy_hash = compute_transaction_hash(buy_transactions)
        
        # Build transaction data structure
        transaction_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "sell_transactions": sell_transactions,
            "buy_transactions": buy_transactions,
            "metadata": {
                "sell_count": len(sell_transactions),
                "buy_count": len(buy_transactions),
                "sell_hash": sell_hash,
                "buy_hash": buy_hash,
                "source_sheet": "Transactions",
                "currency_rates": currency_rates
            }
        }
        
        # Validate structure before saving
        _validate_transaction_structure(transaction_data)
        
        # Save to backend
        backend = _get_storage_backend()
        success = backend.save_transactions(transaction_data)
        
        if success:
            logger.info(
                f"Transactions saved successfully: "
                f"{len(sell_transactions)} sells, {len(buy_transactions)} buys"
            )
        else:
            logger.error("Failed to save transactions to backend")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}", exc_info=True)
        return False
