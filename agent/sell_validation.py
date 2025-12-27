"""
Sell Transaction Validation

Ensures all detected sells have corresponding transaction records.
"""

from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectedSell:
    """Represents a sell detected by comparing snapshots."""
    asset_name: str
    quantity_sold: float
    previous_quantity: float
    current_quantity: float
    category: str


@dataclass
class MissingTransaction:
    """Represents a detected sell without matching transaction."""
    asset_name: str
    quantity_sold: float
    quantity_in_transactions: float
    previous_date: str
    current_date: str
    category: str


class SellValidationError(Exception):
    """Raised when detected sells lack matching transactions."""
    
    def __init__(self, missing_transactions: List[MissingTransaction]):
        self.missing_transactions = missing_transactions
        super().__init__(self._format_error_message())
    
    def _format_error_message(self) -> str:
        """Format detailed error message listing all missing transactions."""
        lines = [
            "",
            "❌ Portfolio snapshot creation FAILED",
            "",
            "Missing sell transaction records detected. All sells must be recorded in",
            "the Transactions sheet before creating a new snapshot.",
            "",
            "Missing Transactions:",
            "─" * 70,
        ]
        
        for i, missing in enumerate(self.missing_transactions, 1):
            lines.append(f"{i}. {missing.asset_name} ({missing.category})")
            lines.append(f"   Detected sell: {missing.quantity_sold:.0f} shares")
            
            if missing.quantity_in_transactions > 0:
                lines.append(f"   Transactions found: {missing.quantity_in_transactions:.0f} shares (PARTIAL)")
                lines.append(f"   Missing: {missing.quantity_sold - missing.quantity_in_transactions:.0f} shares")
            else:
                lines.append(f"   Transactions found: 0 shares")
            
            lines.append(f"   Date range: {missing.previous_date} to {missing.current_date}")
            lines.append(f"   → Please add this transaction to the Transactions sheet")
            lines.append("")
        
        lines.append("─" * 70)
        lines.append("")
        lines.append("To fix:")
        lines.append("1. Open your Google Sheets Transactions tab")
        lines.append("2. Add the missing sell transaction(s):")
        lines.append("   - Date (DD/MM/YYYY format)")
        lines.append("   - Asset Name (must match portfolio exactly - case sensitive)")
        lines.append("   - Quantity (number of shares sold)")
        lines.append("   - Sell Price per unit (with currency symbol)")
        lines.append("3. Run portfolio analysis again")
        lines.append("")
        
        return "\n".join(lines)


def detect_sells(
    current_snapshot: Dict[str, Any],
    previous_snapshot: Dict[str, Any],
    threshold: float = 1.0
) -> List[DetectedSell]:
    """
    Detect sell positions by comparing snapshots.
    
    Args:
        current_snapshot: Current portfolio snapshot
        previous_snapshot: Previous portfolio snapshot
        threshold: Minimum quantity change to consider a sell (default: 1.0 share)
    
    Returns:
        List of DetectedSell objects
    """
    # Build asset dictionaries
    current_assets = {
        asset["name"]: asset 
        for asset in current_snapshot.get("assets", [])
    }
    previous_assets = {
        asset["name"]: asset 
        for asset in previous_snapshot.get("assets", [])
    }
    
    detected_sells = []
    
    # Check all assets from previous snapshot
    for name, prev_asset in previous_assets.items():
        # Skip non-tradable categories
        category = prev_asset.get("category", "")
        if category in ["Pension", "Cash"]:
            continue
        
        previous_qty = prev_asset.get("quantity", 0.0)
        current_qty = current_assets.get(name, {}).get("quantity", 0.0)
        
        qty_change = current_qty - previous_qty
        
        # Detect sells (quantity decreased by at least threshold)
        if qty_change <= -threshold:
            detected_sells.append(DetectedSell(
                asset_name=name,
                quantity_sold=abs(qty_change),
                previous_quantity=previous_qty,
                current_quantity=current_qty,
                category=category
            ))
            logger.info(
                f"Detected sell: {name} - {abs(qty_change):.0f} shares "
                f"({previous_qty:.0f} → {current_qty:.0f})"
            )
    
    return detected_sells


def find_matching_transactions(
    transactions: List[Dict[str, Any]],
    asset_name: str,
    previous_date: str,
    current_date: str
) -> List[Dict[str, Any]]:
    """
    Find transactions matching asset name within date range.
    
    Args:
        transactions: List of all parsed transactions
        asset_name: Asset name to match (case-sensitive exact match)
        previous_date: Start of period (ISO format, exclusive)
        current_date: End of period (ISO format, inclusive)
    
    Returns:
        List of matching transaction dicts
    """
    # Parse date strings
    prev_dt = datetime.fromisoformat(previous_date.replace('Z', '+00:00'))
    curr_dt = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
    
    matching = []
    for txn in transactions:
        # Match asset name (case-sensitive exact match)
        txn_name = txn.get("asset_name", "")
        if txn_name != asset_name:
            continue
        
        # Check date range: previous < txn_date <= current
        txn_date_str = txn.get("date")
        if not txn_date_str:
            continue
        
        # Parse transaction date
        try:
            txn_date = datetime.fromisoformat(txn_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid date format in transaction: {txn_date_str}")
            continue
        
        # Check if within range
        if prev_dt < txn_date <= curr_dt:
            matching.append(txn)
            logger.debug(
                f"Matched transaction: {asset_name} - {txn.get('quantity', 0):.0f} shares "
                f"on {txn_date.date()}"
            )
    
    return matching


def validate_sells_have_transactions(
    current_snapshot: Dict[str, Any],
    previous_snapshot: Dict[str, Any],
    transactions: List[Dict[str, Any]]
) -> None:
    """
    Validates that all detected sells have matching transactions.
    
    Args:
        current_snapshot: Current portfolio snapshot
        previous_snapshot: Previous portfolio snapshot  
        transactions: List of parsed transactions
    
    Raises:
        SellValidationError: If any sell lacks matching transaction
    """
    # Detect all sells
    detected_sells = detect_sells(current_snapshot, previous_snapshot)
    
    if not detected_sells:
        logger.info("No sells detected, validation passed")
        return
    
    logger.info(f"Validating {len(detected_sells)} detected sell(s) against transactions")
    
    # Validate each sell
    missing_transactions = []
    
    for sell in detected_sells:
        # Find matching transactions
        matching_txns = find_matching_transactions(
            transactions=transactions,
            asset_name=sell.asset_name,
            previous_date=previous_snapshot["timestamp"],
            current_date=current_snapshot["timestamp"]
        )
        
        # Sum transaction quantities
        txn_quantity = sum(txn.get("quantity", 0.0) for txn in matching_txns)
        
        # Validate quantity (allow 1.0 share tolerance for rounding)
        quantity_diff = abs(txn_quantity - sell.quantity_sold)
        
        if quantity_diff >= 1.0:
            # Missing or mismatched transaction
            missing_transactions.append(MissingTransaction(
                asset_name=sell.asset_name,
                quantity_sold=sell.quantity_sold,
                quantity_in_transactions=txn_quantity,
                previous_date=previous_snapshot["timestamp"],
                current_date=current_snapshot["timestamp"],
                category=sell.category
            ))
            logger.warning(
                f"Missing transaction: {sell.asset_name} - "
                f"detected {sell.quantity_sold:.0f} shares, "
                f"found {txn_quantity:.0f} in transactions"
            )
        else:
            logger.info(
                f"✓ Validated: {sell.asset_name} - "
                f"{sell.quantity_sold:.0f} shares matched in transactions"
            )
    
    # Raise error if any missing
    if missing_transactions:
        raise SellValidationError(missing_transactions)
    
    logger.info("✓ All detected sells have matching transactions")
