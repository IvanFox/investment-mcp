"""
Daily Portfolio Analysis

Calculates daily changes, attribution analysis, and formats data for
the Daily Overview dashboard view.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from . import storage

logger = logging.getLogger(__name__)


def get_yesterday_snapshot() -> Optional[Dict[str, Any]]:
    """
    Find the snapshot from the previous day.

    Returns:
        Dict containing yesterday's snapshot, or None if not found
    """
    try:
        all_snapshots = storage.get_all_snapshots()

        if not all_snapshots:
            logger.warning("No snapshots available")
            return None

        # Get current date (today)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Look for snapshot from yesterday (24 hours ago)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

        # Find the most recent snapshot from yesterday
        yesterday_snapshots = []
        for snapshot in all_snapshots:
            snap_date = datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))
            if yesterday_start <= snap_date < yesterday_end:
                yesterday_snapshots.append(snapshot)

        if yesterday_snapshots:
            # Return the most recent snapshot from yesterday
            return yesterday_snapshots[-1]

        # If no snapshot from exactly yesterday, find the most recent snapshot
        # that's at least 1 day old
        cutoff = today_start - timedelta(days=1)
        previous_snapshots = []
        for snapshot in all_snapshots:
            snap_date = datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))
            if snap_date < cutoff:
                previous_snapshots.append((snap_date, snapshot))

        if previous_snapshots:
            # Sort by date and return most recent
            previous_snapshots.sort(key=lambda x: x[0], reverse=True)
            logger.info(f"No snapshot from yesterday, using snapshot from {previous_snapshots[0][0].date()}")
            return previous_snapshots[0][1]

        logger.warning("No previous snapshot found for daily comparison")
        return None

    except Exception as e:
        logger.error(f"Error getting yesterday's snapshot: {e}")
        return None


def calculate_daily_changes(
    today_snapshot: Dict[str, Any],
    yesterday_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate daily changes between two snapshots.

    Args:
        today_snapshot: Current portfolio snapshot
        yesterday_snapshot: Previous day's snapshot

    Returns:
        Dict containing:
        - total_change_eur: Total portfolio change in EUR
        - total_change_pct: Total portfolio change percentage
        - asset_changes: List of {name, category, change_eur, change_pct, current_value_eur}
        - yesterday_value_eur: Previous total value
        - today_value_eur: Current total value
    """
    try:
        today_value = today_snapshot.get("total_value_eur", 0)
        yesterday_value = yesterday_snapshot.get("total_value_eur", 0)

        total_change_eur = today_value - yesterday_value
        total_change_pct = (total_change_eur / yesterday_value * 100) if yesterday_value > 0 else 0

        # Build asset lookup for yesterday's values
        yesterday_assets = {}
        for asset in yesterday_snapshot.get("assets", []):
            yesterday_assets[asset["name"]] = asset

        # Calculate changes for each asset
        asset_changes = []
        for today_asset in today_snapshot.get("assets", []):
            name = today_asset["name"]
            category = today_asset.get("category", "Unknown")
            today_asset_value = today_asset.get("current_value_eur", 0)

            # Find corresponding asset in yesterday's snapshot
            yesterday_asset = yesterday_assets.get(name)

            if yesterday_asset:
                yesterday_asset_value = yesterday_asset.get("current_value_eur", 0)
                change_eur = today_asset_value - yesterday_asset_value
                change_pct = (change_eur / yesterday_asset_value * 100) if yesterday_asset_value > 0 else 0
            else:
                # New position
                change_eur = today_asset_value
                change_pct = 100.0

            # Skip assets with zero change and zero value (like empty cash positions)
            if abs(change_eur) < 0.01 and today_asset_value < 0.01:
                continue

            asset_changes.append({
                "name": name,
                "category": category,
                "change_eur": change_eur,
                "change_pct": change_pct,
                "current_value_eur": today_asset_value,
                "previous_value_eur": yesterday_asset.get("current_value_eur", 0) if yesterday_asset else 0
            })

        # Sort by absolute change amount (largest changes first)
        asset_changes.sort(key=lambda x: abs(x["change_eur"]), reverse=True)

        return {
            "total_change_eur": total_change_eur,
            "total_change_pct": total_change_pct,
            "asset_changes": asset_changes,
            "yesterday_value_eur": yesterday_value,
            "today_value_eur": today_value,
            "timestamp_today": today_snapshot.get("timestamp"),
            "timestamp_yesterday": yesterday_snapshot.get("timestamp")
        }

    except Exception as e:
        logger.error(f"Error calculating daily changes: {e}")
        return {
            "total_change_eur": 0,
            "total_change_pct": 0,
            "asset_changes": [],
            "yesterday_value_eur": 0,
            "today_value_eur": 0,
            "error": str(e)
        }


def calculate_attribution(
    asset_changes: List[Dict[str, Any]],
    total_change: float
) -> List[Dict[str, Any]]:
    """
    Calculate attribution - which assets contributed to portfolio change.

    Args:
        asset_changes: List of asset change dicts from calculate_daily_changes()
        total_change: Total portfolio change in EUR

    Returns:
        List of {name, category, change_eur, change_pct, contribution_pct, is_gainer}
        sorted by absolute contribution
    """
    if abs(total_change) < 0.01:
        # No meaningful change to attribute
        return []

    attribution = []
    for asset in asset_changes:
        change_eur = asset["change_eur"]

        # Calculate contribution percentage
        # Contribution = (asset change / total change) * 100
        # Handle positive and negative changes correctly
        contribution_pct = (change_eur / total_change * 100) if total_change != 0 else 0

        attribution.append({
            "name": asset["name"],
            "category": asset["category"],
            "change_eur": change_eur,
            "change_pct": asset["change_pct"],
            "contribution_pct": contribution_pct,
            "current_value_eur": asset["current_value_eur"],
            "is_gainer": change_eur > 0
        })

    # Sort by absolute contribution (most impactful first)
    attribution.sort(key=lambda x: abs(x["contribution_pct"]), reverse=True)

    return attribution


def format_movers_table(
    asset_changes: List[Dict[str, Any]],
    total_change: float,
    top_n: int = 5
) -> str:
    """
    Format top movers as HTML table.

    Args:
        asset_changes: List of asset changes
        total_change: Total portfolio change
        top_n: Number of top movers to show

    Returns:
        HTML string for movers table
    """
    attribution = calculate_attribution(asset_changes, total_change)

    if not attribution:
        return """
        <div class="movers-table-empty">
            <p>No significant changes today</p>
        </div>
        """

    # Get top N movers (by absolute contribution)
    top_movers = attribution[:top_n]

    # Build HTML table
    rows = []
    for mover in top_movers:
        # Determine icon and color
        if mover["is_gainer"]:
            icon = "▲"
            row_class = "gainer"
            change_class = "positive"
        else:
            icon = "▼"
            row_class = "loser"
            change_class = "negative"

        # Format values
        change_str = f"€{abs(mover['change_eur']):,.2f}"
        change_pct_str = f"{mover['change_pct']:+.1f}%"
        contrib_str = f"{abs(mover['contribution_pct']):.0f}%"

        row = f"""
        <tr class="mover-row {row_class}">
            <td class="mover-icon">{icon}</td>
            <td class="mover-name">{mover['name']}</td>
            <td class="mover-change {change_class}">
                {change_str}<br/>
                <span class="mover-pct">{change_pct_str}</span>
            </td>
            <td class="mover-contribution">{contrib_str} of {'gains' if total_change > 0 else 'losses'}</td>
        </tr>
        """
        rows.append(row)

    table_html = f"""
    <div class="movers-table-container">
        <table class="movers-table">
            <thead>
                <tr>
                    <th></th>
                    <th>Asset</th>
                    <th>Change</th>
                    <th>Contribution</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    """

    return table_html


def get_win_loss_ratio(asset_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate win/loss ratio from asset changes.

    Args:
        asset_changes: List of asset changes

    Returns:
        Dict with winners, losers, total counts and ratio
    """
    winners = sum(1 for asset in asset_changes if asset["change_eur"] > 0)
    losers = sum(1 for asset in asset_changes if asset["change_eur"] < 0)
    unchanged = sum(1 for asset in asset_changes if abs(asset["change_eur"]) < 0.01)
    total = len(asset_changes)

    return {
        "winners": winners,
        "losers": losers,
        "unchanged": unchanged,
        "total": total,
        "win_ratio": (winners / total * 100) if total > 0 else 0
    }
