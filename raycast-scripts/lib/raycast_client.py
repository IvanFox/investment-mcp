"""
Client for accessing agent functions from Raycast scripts.

Provides a simple interface to call agent functions and format responses.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path to import agent modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import agent modules
from agent import (
    config,
    storage,
    analysis,
    sheets_connector,
    events_tracker,
    insider_trading,
)


class RaycastClient:
    """Client for accessing portfolio agent functions."""

    def __init__(self):
        """Initialize the client."""
        # Ensure config is loaded
        config.get_config()

    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Get current portfolio status with all positions from latest snapshot.

        Returns:
            Dictionary with portfolio status data matching TypeScript interface
        """
        latest_snapshot = storage.get_latest_snapshot()

        if not latest_snapshot:
            return {
                "error": "No snapshots available",
                "message": "Run run_portfolio_analysis() to create the first snapshot.",
            }

        # Organize positions by category
        organized = analysis.organize_positions_by_category(latest_snapshot)

        # Transform to match TypeScript interface:
        # - Flatten nested categories.categories to categories
        # - Rename total_value -> value
        # - Rename gain_loss_percent -> gain_loss_pct in positions
        # - Add count field
        # - Add last_fetch and source fields
        categories_data = {}

        # Extract the nested categories structure
        nested_categories = organized.get("categories", {})

        for category_name, category_info in nested_categories.items():
            # Transform positions to match TypeScript interface
            positions = []
            for pos in category_info.get("positions", []):
                transformed_pos = {
                    "name": pos.get("name"),
                    "quantity": pos.get("quantity"),
                    "current_value_eur": pos.get("current_value_eur"),
                    "purchase_price_total_eur": pos.get("purchase_price_total_eur"),
                    "gain_loss_eur": pos.get("gain_loss_eur"),
                    "gain_loss_pct": pos.get("gain_loss_percent", 0.0),  # Rename field
                }
                positions.append(transformed_pos)

            categories_data[category_name] = {
                "value": category_info.get("total_value", 0.0),
                "percentage": category_info.get("percentage", 0.0),
                "count": len(category_info.get("positions", [])),
                "positions": positions,
            }

        return {
            "total_value_eur": latest_snapshot.get("total_value_eur", 0.0),
            "asset_count": len(latest_snapshot.get("assets", [])),
            "last_fetch": latest_snapshot.get("timestamp"),
            "source": "Google Sheets",
            "categories": categories_data,
        }

        # Organize positions by category
        organized = analysis.organize_positions_by_category(latest_snapshot)

        # Transform to match TypeScript interface:
        # - Flatten nested categories.categories to categories
        # - Rename total_value -> value
        # - Add count field
        # - Add last_fetch and source fields
        categories_data = {}

        # Extract the nested categories structure
        nested_categories = organized.get("categories", {})

        for category_name, category_info in nested_categories.items():
            categories_data[category_name] = {
                "value": category_info.get("total_value", 0.0),
                "percentage": category_info.get("percentage", 0.0),
                "count": len(category_info.get("positions", [])),
                "positions": category_info.get("positions", []),
            }

        return {
            "total_value_eur": latest_snapshot.get("total_value_eur", 0.0),
            "asset_count": len(latest_snapshot.get("assets", [])),
            "last_fetch": latest_snapshot.get("timestamp"),
            "source": "Google Sheets",
            "categories": categories_data,
        }

        # Organize positions by category
        organized = analysis.organize_positions_by_category(latest_snapshot)

        return {
            "total_value_eur": latest_snapshot.get("total_value_eur", 0.0),
            "timestamp": latest_snapshot.get("timestamp"),
            "asset_count": len(latest_snapshot.get("assets", [])),
            "categories": organized,
        }

    def get_quick_analysis(self) -> Dict[str, Any]:
        """
        Quick analysis comparing current spreadsheet state vs last snapshot.

        Returns:
            Dictionary with quick analysis data
        """
        # Fetch current data from spreadsheet
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        current_snapshot = analysis.create_portfolio_snapshot(normalized_data)

        # Get last snapshot
        last_snapshot = storage.get_latest_snapshot()

        if not last_snapshot:
            return {
                "current_status": {
                    "total_value_eur": current_snapshot.get("total_value_eur", 0.0),
                    "timestamp": current_snapshot.get("timestamp"),
                    "asset_count": len(current_snapshot.get("assets", [])),
                },
                "message": "No previous snapshot for comparison. Run run_portfolio_analysis() to create the first snapshot.",
            }

        # Load transactions for comparison
        transactions_data = storage.get_transactions()
        sell_transactions = transactions_data.get("sell_transactions", [])
        buy_transactions = transactions_data.get("buy_transactions", [])
        
        # Compare current vs last
        comparison = analysis.compare_snapshots(
            last_snapshot,
            current_snapshot,
            sell_transactions,
            buy_transactions
        )

        # Get top movers (winners) and bottom movers (losers)
        # Build enriched winners/losers with current values from snapshot
        winners = []
        for mover in comparison.get("top_movers", [])[:5]:
            asset = next(
                (a for a in current_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            if asset:
                winners.append({
                    "name": mover["name"],
                    "change_eur": mover["change_eur"],
                    "change_pct": round((mover["change_eur"] / asset.get("current_value_eur", 1) * 100), 2),
                    "current_value_eur": asset.get("current_value_eur", 0),
                })
        
        losers = []
        for mover in comparison.get("bottom_movers", [])[:5]:
            asset = next(
                (a for a in current_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            if asset:
                losers.append({
                    "name": mover["name"],
                    "change_eur": mover["change_eur"],
                    "change_pct": round((mover["change_eur"] / asset.get("current_value_eur", 1) * 100), 2),
                    "current_value_eur": asset.get("current_value_eur", 0),
                })

        return {
            "current_status": {
                "total_value_eur": current_snapshot.get("total_value_eur", 0.0),
                "timestamp": current_snapshot.get("timestamp"),
                "asset_count": len(current_snapshot.get("assets", [])),
            },
            "snapshot_comparison": {
                "snapshot_date": last_snapshot.get("timestamp"),
                "value_change": {
                    "eur": comparison.get("total_value_change_eur", 0),
                    "percentage": comparison.get("total_value_change_percent", 0),
                    "direction": "up"
                    if comparison.get("total_value_change_eur", 0) >= 0
                    else "down",
                },
            },
            "winners": winners,
            "losers": losers,
        }

    def get_winners_losers(self) -> Dict[str, Any]:
        """
        Get top winners and losers from last two snapshots.

        Returns:
            Dictionary with winners/losers data
        """
        # Get last 2 snapshots
        all_snapshots = storage.get_all_snapshots()

        if len(all_snapshots) < 2:
            return {
                "error": "Insufficient snapshots",
                "message": "Need at least 2 snapshots for comparison. Run run_portfolio_analysis() to create snapshots.",
                "snapshots_available": len(all_snapshots),
            }

        # Get the two most recent snapshots (last = most recent, second-to-last = previous)
        latest_snapshot = all_snapshots[-1]
        previous_snapshot = all_snapshots[-2]

        # Load transactions for comparison
        transactions_data = storage.get_transactions()
        sell_transactions = transactions_data.get("sell_transactions", [])
        buy_transactions = transactions_data.get("buy_transactions", [])
        
        # Compare snapshots (previous as old, latest as new)
        comparison = analysis.compare_snapshots(
            previous_snapshot,
            latest_snapshot,
            sell_transactions,
            buy_transactions
        )

        # Build enriched winners/losers with current values from latest snapshot
        winners = []
        for mover in comparison.get("top_movers", [])[:5]:
            asset = next(
                (a for a in latest_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            prev_asset = next(
                (a for a in previous_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            if asset and prev_asset:
                current_val = asset.get("current_value_eur", 0)
                prev_val = prev_asset.get("current_value_eur", 1)
                winners.append({
                    "name": mover["name"],
                    "change_eur": mover["change_eur"],
                    "change_pct": round((mover["change_eur"] / prev_val * 100) if prev_val > 0 else 0, 2),
                    "current_value_eur": current_val,
                })
        
        losers = []
        for mover in comparison.get("bottom_movers", [])[:5]:
            asset = next(
                (a for a in latest_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            prev_asset = next(
                (a for a in previous_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            if asset and prev_asset:
                current_val = asset.get("current_value_eur", 0)
                prev_val = prev_asset.get("current_value_eur", 1)
                losers.append({
                    "name": mover["name"],
                    "change_eur": mover["change_eur"],
                    "change_pct": round((mover["change_eur"] / prev_val * 100) if prev_val > 0 else 0, 2),
                    "current_value_eur": current_val,
                })

        # Calculate days between snapshots
        from datetime import datetime

        try:
            prev_time = datetime.fromisoformat(
                previous_snapshot["timestamp"].replace("Z", "+00:00")
            )
            latest_time = datetime.fromisoformat(
                latest_snapshot["timestamp"].replace("Z", "+00:00")
            )
            days_diff = (latest_time - prev_time).days
        except:
            days_diff = 0

        return {
            "comparison_period": {
                "from": previous_snapshot["timestamp"],
                "to": latest_snapshot["timestamp"],
                "days": days_diff,
            },
            "portfolio_change": {
                "value_eur": comparison.get("total_value_change_eur", 0),
                "percentage": comparison.get("total_value_change_percent", 0),
                "direction": "up"
                if comparison.get("total_value_change_eur", 0) >= 0
                else "down",
            },
            "winners": winners,
            "losers": losers,
        }

    def get_upcoming_events(self) -> Dict[str, Any]:
        """
        Get upcoming earnings events for portfolio stocks.

        Returns:
            Dictionary with upcoming events data
        """
        # Fetch current portfolio data
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)

        # Get upcoming events
        return events_tracker.get_portfolio_upcoming_events(normalized_data)

    def get_portfolio_insider_trades(self) -> Dict[str, Any]:
        """
        Get insider trading data for all portfolio stocks.

        Returns:
            Dictionary with insider trading data
        """
        # Fetch current portfolio data
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)

        # Get insider trades
        return insider_trading.get_portfolio_insider_trades(normalized_data)

    def get_ticker_insider_trades(self, ticker: str) -> Dict[str, Any]:
        """
        Get insider trading data for a specific ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            Dictionary with insider trading data
        """
        return insider_trading.get_insider_trades_for_ticker(ticker)

    def get_daily_performance(self) -> Dict[str, Any]:
        """
        Get top 5 stock winners and losers based on daily change percentage.
        
        Fetches live data from spreadsheet and sorts by daily_change_pct.
        Only includes stocks (US + EU), excludes Bonds, ETFs, Pension, Cash.
        
        Returns:
            Dictionary with daily performance data including:
            - winners: Top 5 stocks with highest daily_change_pct
            - losers: Top 5 stocks with lowest daily_change_pct
            - Each entry includes: name, category, daily_change_pct, 
              current_value_eur, change_value_eur (monetary impact)
        """
        from datetime import datetime, timezone
        
        # Fetch current data from spreadsheet
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Filter to stocks only (exclude Bonds, ETFs, Pension, Cash)
        stocks = [
            asset for asset in normalized_data 
            if asset.get("category") in ["US Stocks", "EU Stocks"]
        ]
        
        if not stocks:
            return {
                "error": "No stock data available",
                "message": "No stocks found in portfolio. Add stocks to track daily performance.",
            }
        
        # Calculate monetary impact (change_value_eur) for each stock
        # Formula: current_value_eur * (daily_change_pct / 100)
        enriched_stocks = []
        for stock in stocks:
            daily_pct = stock.get("daily_change_pct", 0.0)
            current_value = stock.get("current_value_eur", 0.0)
            
            # Calculate monetary impact
            # If stock is +5%, then change_value = current_value * 0.05 / (1 + 0.05)
            # Simplification: change_value ≈ current_value * (daily_pct / 100)
            change_value_eur = current_value * (daily_pct / 100.0)
            
            enriched_stocks.append({
                "name": stock.get("name"),
                "category": stock.get("category"),
                "quantity": stock.get("quantity", 0.0),
                "current_value_eur": current_value,
                "daily_change_pct": daily_pct,
                "change_value_eur": round(change_value_eur, 2),
            })
        
        # Sort by daily_change_pct
        sorted_stocks = sorted(enriched_stocks, key=lambda x: x["daily_change_pct"], reverse=True)
        
        # Top 5 winners (highest positive change)
        winners = [s for s in sorted_stocks if s["daily_change_pct"] > 0][:5]
        
        # Top 5 losers (lowest negative change)
        losers = [s for s in sorted_stocks if s["daily_change_pct"] < 0][-5:]
        losers.reverse()  # Show worst first
        
        # Calculate summary statistics
        total_change_value = sum(s["change_value_eur"] for s in enriched_stocks)
        avg_change_pct = sum(s["daily_change_pct"] for s in enriched_stocks) / len(enriched_stocks) if enriched_stocks else 0.0
        
        return {
            "winners": winners,
            "losers": losers,
            "summary": {
                "total_stocks": len(enriched_stocks),
                "total_change_value_eur": round(total_change_value, 2),
                "average_change_pct": round(avg_change_pct, 2),
                "winners_count": len(winners),
                "losers_count": len(losers),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
