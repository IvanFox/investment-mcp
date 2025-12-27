"""
Buy Transaction Validation

Ensures all detected buys have corresponding transaction records.
"""

from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectedBuy:
    """Represents a buy detected by comparing snapshots."""
    asset_name: str
    quantity_bought: float
    previous_quantity: float
    current_quantity: float
    category: str
    is_new_position: bool = False


@dataclass
class MissingBuyTransaction:
    """Represents a detected buy without matching transaction."""
    asset_name: str
    quantity_bought: float
    quantity_in_transactions: float
    previous_date: str
    current_date: str
    category: str
    is_new_position: bool = False


class BuyValidationError(Exception):
    """Raised when detected buys lack matching transactions."""
    
    def __init__(self, missing_transactions: List[MissingBuyTransaction]):
        self.missing_transactions = missing_transactions
        super().__init__(self._format_error_message())
    
    def _format_error_message(self) -> str:
        """Format detailed error message listing all missing transactions."""
        lines = [
            "",
            "❌ Portfolio snapshot creation FAILED",
            "",
            "Missing buy transaction records detected. All purchases must be recorded in",
            "the Transactions sheet (Buy section, columns J-M) before creating a new snapshot.",
            "",
            "Missing Transactions:",
            "─" * 70,
        ]
        
        for i, missing in enumerate(self.missing_transactions, 1):
            if missing.is_new_position:
                lines.append(f"{i}. {missing.asset_name} ({missing.category}) - NEW POSITION")
                lines.append(f"   Detected buy: {missing.quantity_bought:.0f} shares (new position)")
            else:
                lines.append(f"{i}. {missing.asset_name} ({missing.category})")
                lines.append(f"   Detected buy: {missing.quantity_bought:.0f} shares")
            
            if missing.quantity_in_transactions > 0:
                lines.append(f"   Transactions found: {missing.quantity_in_transactions:.0f} shares (PARTIAL)")
                lines.append(f"   Missing: {missing.quantity_bought - missing.quantity_in_transactions:.0f} shares")
            else:
                lines.append(f"   Transactions found: 0 shares")
            
            if missing.is_new_position:
                lines.append(f"   Date range: N/A (new position, must record initial purchase)")
            else:
                lines.append(f"   Date range: {missing.previous_date} to {missing.current_date}")
            
            lines.append(f"   → Please add this transaction to the Transactions sheet (Buy section)")
            lines.append("")
        
        lines.append("─" * 70)
        lines.append("")
        lines.append("To fix:")
        lines.append("1. Open your Google Sheets Transactions tab")
        lines.append("2. Add the missing buy transaction(s) in columns J-M (Buy section):")
        lines.append("   - Column J: Date (DD/MM/YYYY format)")
        lines.append("   - Column K: Asset Name (must match portfolio exactly - case sensitive)")
        lines.append("   - Column L: Quantity (number of shares purchased)")
        lines.append("   - Column M: Purchase Price per unit (with currency symbol: £, $, or €)")
        lines.append("3. Run portfolio analysis again")
        lines.append("")
        
        return "\n".join(lines)


def detect_buys(
    current_snapshot: Dict[str, Any],
    previous_snapshot: Dict[str, Any],
    threshold: float = 1.0
) -> List[DetectedBuy]:
    """
    Detect buy positions by comparing snapshots.
    
    Args:
        current_snapshot: Current portfolio snapshot
        previous_snapshot: Previous portfolio snapshot
        threshold: Minimum quantity change to consider a buy (default: 1.0 share)
    
    Returns:
        List of DetectedBuy objects
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
    
    detected_buys = []
    
    # Check all assets from current snapshot for quantity increases
    for name, curr_asset in current_assets.items():
        # Skip non-tradable categories
        category = curr_asset.get("category", "")
        if category in ["Pension", "Cash"]:
            continue
        
        current_qty = curr_asset.get("quantity", 0.0)
        previous_qty = previous_assets.get(name, {}).get("quantity", 0.0)
        
        qty_change = current_qty - previous_qty
        
        # Detect buys (quantity increased by at least threshold)
        if qty_change >= threshold:
            is_new_position = name not in previous_assets
            
            detected_buys.append(DetectedBuy(
                asset_name=name,
                quantity_bought=qty_change,
                previous_quantity=previous_qty,
                current_quantity=current_qty,
                category=category,
                is_new_position=is_new_position
            ))
            
            if is_new_position:
                logger.info(
                    f"Detected NEW POSITION: {name} - {qty_change:.0f} shares "
                    f"(0 → {current_qty:.0f})"
                )
            else:
                logger.info(
                    f"Detected buy: {name} - {qty_change:.0f} shares "
                    f"({previous_qty:.0f} → {current_qty:.0f})"
                )
    
    return detected_buys


def find_matching_buy_transactions(
    transactions: List[Dict[str, Any]],
    asset_name: str,
    previous_date: str,
    current_date: str
) -> List[Dict[str, Any]]:
    """
    Find buy transactions matching asset name within date range.
    
    Args:
        transactions: List of all parsed buy transactions
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
            logger.warning(f"Invalid date format in buy transaction: {txn_date_str}")
            continue
        
        # Check if within range
        if prev_dt < txn_date <= curr_dt:
            matching.append(txn)
            logger.debug(
                f"Matched buy transaction: {asset_name} - {txn.get('quantity', 0):.0f} shares "
                f"on {txn_date.date()}"
            )
    
    return matching


def validate_buys_have_transactions(
    current_snapshot: Dict[str, Any],
    previous_snapshot: Dict[str, Any],
    buy_transactions: List[Dict[str, Any]]
) -> None:
    """
    Validates that all detected buys have matching transactions.
    
    Args:
        current_snapshot: Current portfolio snapshot
        previous_snapshot: Previous portfolio snapshot  
        buy_transactions: List of parsed buy transactions
    
    Raises:
        BuyValidationError: If any buy lacks matching transaction
    """
    # Detect all buys (including new positions)
    detected_buys = detect_buys(current_snapshot, previous_snapshot)
    
    if not detected_buys:
        logger.info("No buys detected, validation passed")
        return
    
    logger.info(f"Validating {len(detected_buys)} detected buy(s) against transactions")
    
    # Validate each buy
    missing_transactions = []
    
    for buy in detected_buys:
        # Find matching transactions
        matching_txns = find_matching_buy_transactions(
            transactions=buy_transactions,
            asset_name=buy.asset_name,
            previous_date=previous_snapshot["timestamp"],
            current_date=current_snapshot["timestamp"]
        )
        
        # Sum transaction quantities
        txn_quantity = sum(txn.get("quantity", 0.0) for txn in matching_txns)
        
        # Validate quantity (allow 1.0 share tolerance for rounding)
        quantity_diff = abs(txn_quantity - buy.quantity_bought)
        
        if quantity_diff >= 1.0:
            # Missing or mismatched transaction
            missing_transactions.append(MissingBuyTransaction(
                asset_name=buy.asset_name,
                quantity_bought=buy.quantity_bought,
                quantity_in_transactions=txn_quantity,
                previous_date=previous_snapshot["timestamp"],
                current_date=current_snapshot["timestamp"],
                category=buy.category,
                is_new_position=buy.is_new_position
            ))
            
            if buy.is_new_position:
                logger.warning(
                    f"Missing transaction for NEW POSITION: {buy.asset_name} - "
                    f"detected {buy.quantity_bought:.0f} shares, "
                    f"found {txn_quantity:.0f} in transactions"
                )
            else:
                logger.warning(
                    f"Missing transaction: {buy.asset_name} - "
                    f"detected {buy.quantity_bought:.0f} shares, "
                    f"found {txn_quantity:.0f} in transactions"
                )
        else:
            if buy.is_new_position:
                logger.info(
                    f"✓ Validated NEW POSITION: {buy.asset_name} - "
                    f"{buy.quantity_bought:.0f} shares matched in transactions"
                )
            else:
                logger.info(
                    f"✓ Validated: {buy.asset_name} - "
                    f"{buy.quantity_bought:.0f} shares matched in transactions"
                )
    
    # Raise error if any missing
    if missing_transactions:
        raise BuyValidationError(missing_transactions)
    
    logger.info("✓ All detected buys have matching transactions")
