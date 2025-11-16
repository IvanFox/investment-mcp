"""
Core Analysis & Snapshot Logic

This module contains the business logic for creating snapshots and comparing them.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def create_portfolio_snapshot(normalized_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Creates a complete snapshot of the portfolio at a single point in time.

    Args:
        normalized_data: List of asset dictionaries from parse_and_normalize_data

    Returns:
        dict: Snapshot conforming to the Snapshot JSON Schema:
        {
            "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
            "total_value_eur": 123456.78,
            "assets": [
                {
                    "name": "Intel Corp",
                    "quantity": 55,
                    "purchase_price_total_eur": 2335.71,
                    "current_value_eur": 1050.27,
                    "category": "Tech"
                }
            ]
        }
    """
    try:
        # Generate current UTC timestamp in ISO 8601 format
        timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate total value by summing current_value_eur of all assets
        total_value_eur = sum(
            asset.get("current_value_eur", 0.0) for asset in normalized_data
        )

        # Create snapshot
        snapshot = {
            "timestamp": timestamp,
            "total_value_eur": round(total_value_eur, 2),
            "assets": normalized_data.copy(),
        }

        logger.info(
            f"Created portfolio snapshot with {len(normalized_data)} assets, total value: €{total_value_eur:.2f}"
        )
        return snapshot

    except Exception as e:
        logger.error(f"Failed to create portfolio snapshot: {e}")
        raise


def compare_snapshots(
    current_snapshot: Dict[str, Any], previous_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Performs week-over-week comparison and generates a structured report object.

    Args:
        current_snapshot: Current snapshot dictionary
        previous_snapshot: Previous snapshot dictionary

    Returns:
        dict: Analysis report with schema:
        {
            "total_value_change_eur": float,
            "total_value_change_percent": float,
            "top_movers": [{"name": str, "change_eur": float}, ...],
            "bottom_movers": [{"name": str, "change_eur": float}, ...],
            "new_positions": [{"name": str, "quantity": float, "current_value_eur": float}, ...],
            "sold_positions": [{"name": str, "realized_gain_loss_eur": float}, ...]
        }
    """
    try:
        # Create sets of asset names for efficient comparison
        current_assets = {
            asset["name"]: asset for asset in current_snapshot.get("assets", [])
        }
        previous_assets = {
            asset["name"]: asset for asset in previous_snapshot.get("assets", [])
        }

        current_names = set(current_assets.keys())
        previous_names = set(previous_assets.keys())

        # Identify asset categories
        held_names = current_names & previous_names
        new_names = current_names - previous_names
        sold_names = previous_names - current_names

        logger.info(
            f"Portfolio comparison: {len(held_names)} held, {len(new_names)} new, {len(sold_names)} sold"
        )

        # Analyze held assets
        asset_changes = []
        for name in held_names:
            current_asset = current_assets[name]
            previous_asset = previous_assets[name]

            current_value = current_asset.get("current_value_eur", 0.0)
            previous_value = previous_asset.get("current_value_eur", 0.0)
            current_qty = current_asset.get("quantity", 0.0)
            previous_qty = previous_asset.get("quantity", 0.0)

            # Check if quantity changed
            if abs(current_qty - previous_qty) > 0.01:
                # Normalize value change to account for quantity change
                # Calculate what the current value would be if quantity hadn't changed
                if current_qty > 0 and previous_qty > 0:
                    current_price_per_share = current_value / current_qty
                    normalized_current_value = current_price_per_share * previous_qty
                    change_eur = normalized_current_value - previous_value
                else:
                    # Edge case: all shares sold or quantity is zero
                    change_eur = 0.0
            else:
                # No quantity change, use actual value change
                change_eur = current_value - previous_value

            asset_changes.append({"name": name, "change_eur": round(change_eur, 2)})

        # Sort by absolute change to find top movers
        asset_changes.sort(key=lambda x: abs(x["change_eur"]), reverse=True)

        # Get top 5 gainers and top 5 losers
        positive_changes = [
            change for change in asset_changes if change["change_eur"] > 0
        ]
        negative_changes = [
            change for change in asset_changes if change["change_eur"] < 0
        ]

        top_movers = positive_changes[:5] if positive_changes else []
        bottom_movers = negative_changes[:5] if negative_changes else []

        # Track quantity changes for held positions
        quantity_changes = []
        QUANTITY_CHANGE_THRESHOLD = 0.01  # Ignore changes < 0.01 shares

        for name in held_names:
            current_asset = current_assets[name]
            previous_asset = previous_assets[name]

            current_qty = current_asset.get("quantity", 0.0)
            previous_qty = previous_asset.get("quantity", 0.0)
            qty_change = current_qty - previous_qty

            # Only track significant quantity changes
            if abs(qty_change) > QUANTITY_CHANGE_THRESHOLD:
                current_value = current_asset.get("current_value_eur", 0.0)
                previous_value = previous_asset.get("current_value_eur", 0.0)

                # Calculate price per share
                current_price_per_share = (
                    current_value / current_qty if current_qty > 0 else 0
                )
                previous_price_per_share = (
                    previous_value / previous_qty if previous_qty > 0 else 0
                )

                change_info = {
                    "name": name,
                    "category": current_asset.get("category", "Unknown"),
                    "previous_quantity": previous_qty,
                    "current_quantity": current_qty,
                    "quantity_change": qty_change,
                    "change_type": "purchase" if qty_change > 0 else "sale",
                    "current_price_per_share_eur": round(current_price_per_share, 2),
                    "previous_price_per_share_eur": round(previous_price_per_share, 2),
                    "current_total_value_eur": current_value,
                    "value_change_eur": round(current_value - previous_value, 2),
                }
                quantity_changes.append(change_info)

        # Sort quantity changes: purchases first (by quantity desc), then sales (by abs quantity desc)
        quantity_changes.sort(
            key=lambda x: (x["change_type"] == "sale", -abs(x["quantity_change"]))
        )

        # Analyze new positions
        new_positions = []
        for name in new_names:
            asset = current_assets[name]
            new_positions.append(
                {
                    "name": name,
                    "quantity": asset.get("quantity", 0.0),
                    "current_value_eur": asset.get("current_value_eur", 0.0),
                }
            )

        # Analyze sold positions
        sold_positions = []
        for name in sold_names:
            asset = previous_assets[name]
            purchase_price = asset.get("purchase_price_total_eur", 0.0)
            last_value = asset.get("current_value_eur", 0.0)

            # Calculate realized gain/loss (approximated by last snapshot value)
            realized_gain_loss = last_value - purchase_price

            sold_positions.append(
                {"name": name, "realized_gain_loss_eur": round(realized_gain_loss, 2)}
            )

        # Calculate total portfolio changes
        current_total = current_snapshot.get("total_value_eur", 0.0)
        previous_total = previous_snapshot.get("total_value_eur", 0.0)

        total_change_eur = current_total - previous_total
        total_change_percent = (
            (total_change_eur / previous_total * 100) if previous_total > 0 else 0.0
        )

        # Construct report
        report = {
            "total_value_change_eur": round(total_change_eur, 2),
            "total_value_change_percent": round(total_change_percent, 2),
            "top_movers": top_movers,
            "bottom_movers": bottom_movers,
            "quantity_changes": quantity_changes,
            "new_positions": new_positions,
            "sold_positions": sold_positions,
        }

        logger.info(
            f"Portfolio analysis complete: €{total_change_eur:.2f} ({total_change_percent:.2f}%) change"
        )
        return report

    except Exception as e:
        logger.error(f"Failed to compare snapshots: {e}")
        raise


def organize_positions_by_category(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Organizes portfolio positions by category with aggregated statistics.

    Args:
        snapshot: Portfolio snapshot dictionary

    Returns:
        dict: Organized positions by category with structure:
        {
            "timestamp": str,
            "total_value_eur": float,
            "categories": {
                "US Stocks": {
                    "total_value": float,
                    "percentage": float,
                    "positions": [
                        {
                            "name": str,
                            "quantity": float,
                            "current_value_eur": float,
                            "purchase_price_total_eur": float,
                            "gain_loss_eur": float,
                            "gain_loss_percent": float
                        }
                    ]
                }
            }
        }
    """
    try:
        timestamp = snapshot.get("timestamp", "Unknown")
        total_value_eur = snapshot.get("total_value_eur", 0.0)
        assets = snapshot.get("assets", [])

        categories = {}

        for asset in assets:
            category = asset.get("category", "Other")

            if category not in categories:
                categories[category] = {
                    "total_value": 0.0,
                    "percentage": 0.0,
                    "positions": [],
                }

            current_value = asset.get("current_value_eur", 0.0)
            purchase_price = asset.get("purchase_price_total_eur", 0.0)
            quantity = asset.get("quantity", 0.0)

            gain_loss_eur = current_value - purchase_price
            gain_loss_percent = (
                (gain_loss_eur / purchase_price * 100) if purchase_price > 0 else 0.0
            )

            position = {
                "name": asset.get("name", "Unknown"),
                "quantity": quantity,
                "current_value_eur": current_value,
                "purchase_price_total_eur": purchase_price,
                "gain_loss_eur": round(gain_loss_eur, 2),
                "gain_loss_percent": round(gain_loss_percent, 2),
            }

            categories[category]["positions"].append(position)
            categories[category]["total_value"] += current_value

        for category_name, category_data in categories.items():
            category_data["total_value"] = round(category_data["total_value"], 2)
            category_data["percentage"] = (
                round((category_data["total_value"] / total_value_eur * 100), 2)
                if total_value_eur > 0
                else 0.0
            )
            category_data["positions"].sort(
                key=lambda x: x["current_value_eur"], reverse=True
            )

        result = {
            "timestamp": timestamp,
            "total_value_eur": total_value_eur,
            "categories": categories,
        }

        logger.info(
            f"Organized {len(assets)} positions into {len(categories)} categories"
        )
        return result

    except Exception as e:
        logger.error(f"Failed to organize positions by category: {e}")
        raise
