"""
Raycast Tools Module

JSON-focused wrappers around agent functionality for Raycast Script Commands.
All functions return structured JSON (not markdown).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from . import sheets_connector
from . import storage
from . import analysis
from . import events_tracker
from . import insider_trading

logger = logging.getLogger(__name__)


def get_portfolio_status_json() -> Dict[str, Any]:
    """
    Get current portfolio status directly from Google Sheets (live data).
    
    IMPORTANT:
    - READ-ONLY operation (does NOT create snapshot)
    - Fetches current data from spreadsheet
    - Positions sorted by value (largest first) within each category
    - Categories sorted by total value (largest first)
    
    Returns:
        dict: Portfolio status with structure:
        {
            "success": true,
            "data": {
                "total_value_eur": 405303.56,
                "asset_count": 42,
                "last_fetch": "2025-12-27T10:00:00Z",
                "source": "google_sheets",
                "categories": {...}
            },
            "metadata": {...}
        }
    """
    try:
        logger.info("Fetching live portfolio data from Google Sheets...")
        
        # Fetch current live data from sheets
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Calculate totals
        total_value_eur = sum(
            asset.get("current_value_eur", 0.0) for asset in normalized_data
        )
        
        # Organize by category
        categories = {}
        for asset in normalized_data:
            category = asset.get("category", "Unknown")
            
            if category not in categories:
                categories[category] = {
                    "value": 0.0,
                    "percentage": 0.0,
                    "count": 0,
                    "positions": []
                }
            
            # Build position object
            current_value = asset.get("current_value_eur", 0.0)
            purchase_price = asset.get("purchase_price_total_eur", 0.0)
            gain_loss = current_value - purchase_price
            gain_loss_pct = (gain_loss / purchase_price * 100) if purchase_price > 0 else 0
            
            position = {
                "name": asset.get("name", "Unknown"),
                "quantity": asset.get("quantity", 0.0),
                "current_value_eur": round(current_value, 2),
                "purchase_price_total_eur": round(purchase_price, 2),
                "gain_loss_eur": round(gain_loss, 2),
                "gain_loss_pct": round(gain_loss_pct, 2)
            }
            
            categories[category]["positions"].append(position)
            categories[category]["value"] += current_value
            categories[category]["count"] += 1
        
        # Calculate percentages and sort positions by value (LARGEST FIRST)
        for category_name, category_data in categories.items():
            category_data["value"] = round(category_data["value"], 2)
            category_data["percentage"] = round(
                (category_data["value"] / total_value_eur * 100) if total_value_eur > 0 else 0,
                2
            )
            # Sort positions by value descending (largest first)
            category_data["positions"].sort(
                key=lambda x: x["current_value_eur"],
                reverse=True
            )
        
        # Sort categories by value descending (largest first)
        sorted_categories = dict(
            sorted(categories.items(), key=lambda x: x[1]["value"], reverse=True)
        )
        
        return {
            "success": True,
            "data": {
                "total_value_eur": round(total_value_eur, 2),
                "asset_count": len(normalized_data),
                "last_fetch": datetime.now(timezone.utc).isoformat(),
                "source": "google_sheets",
                "categories": sorted_categories
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "investment-mcp",
                "data_source": "google_sheets_live",
                "read_only": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get portfolio status: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def get_quick_analysis_json(winners_losers_limit: int = 5) -> Dict[str, Any]:
    """
    Compare current portfolio (live) vs latest snapshot.
    
    Behavior:
    - Fetches live data from Google Sheets
    - Compares with latest snapshot from storage
    - Shows top gainers/losers
    - Does NOT create new snapshot (read-only)
    
    Args:
        winners_losers_limit: Number of top/bottom movers (default: 5)
    
    Returns:
        dict: Quick analysis with current status and comparison
    """
    try:
        logger.info("Performing quick analysis: live data vs latest snapshot...")
        
        # 1. Fetch LIVE data from Google Sheets
        raw_data = sheets_connector.fetch_portfolio_data()
        current_normalized = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Create a pseudo-snapshot from live data (for comparison purposes)
        current_live_snapshot = analysis.create_portfolio_snapshot(current_normalized)
        
        # 2. Get latest SAVED snapshot
        latest_snapshot = storage.get_latest_snapshot()
        
        if not latest_snapshot:
            # No snapshot exists yet - return just current status
            return {
                "success": True,
                "data": {
                    "current_status": {
                        "total_value_eur": round(current_live_snapshot.get("total_value_eur", 0), 2),
                        "asset_count": len(current_normalized),
                        "source": "google_sheets",
                        "timestamp": current_live_snapshot.get("timestamp")
                    },
                    "snapshot_comparison": None,
                    "winners": [],
                    "losers": [],
                    "summary": {
                        "message": "No snapshot available for comparison. Run portfolio_analysis() to create first snapshot."
                    }
                },
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "investment-mcp",
                    "comparison": "none"
                }
            }
        
        # 3. Load transactions for comparison
        transactions_data = storage.get_transactions()
        sell_transactions = transactions_data.get("sell_transactions", [])
        buy_transactions = transactions_data.get("buy_transactions", [])
        
        # 4. Compare live data vs latest snapshot
        comparison = analysis.compare_snapshots(
            current_live_snapshot,
            latest_snapshot,
            sell_transactions,
            buy_transactions
        )
        
        # 5. Build winners list with enriched data
        winners = []
        for mover in comparison.get("top_movers", [])[:winners_losers_limit]:
            # Find asset in current live data
            current_asset = next(
                (a for a in current_normalized if a["name"] == mover["name"]),
                None
            )
            snapshot_asset = next(
                (a for a in latest_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            
            if current_asset and snapshot_asset:
                current_val = current_asset.get("current_value_eur", 0)
                snapshot_val = snapshot_asset.get("current_value_eur", 0)
                
                winners.append({
                    "name": mover["name"],
                    "change_eur": round(mover["change_eur"], 2),
                    "change_pct": round((mover["change_eur"] / snapshot_val * 100) if snapshot_val > 0 else 0, 2),
                    "current_value_eur": round(current_val, 2),
                    "snapshot_value_eur": round(snapshot_val, 2),
                    "category": current_asset.get("category", "Unknown")
                })
        
        # 5. Build losers list
        losers = []
        for mover in comparison.get("bottom_movers", [])[:winners_losers_limit]:
            current_asset = next(
                (a for a in current_normalized if a["name"] == mover["name"]),
                None
            )
            snapshot_asset = next(
                (a for a in latest_snapshot.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            
            if current_asset and snapshot_asset:
                current_val = current_asset.get("current_value_eur", 0)
                snapshot_val = snapshot_asset.get("current_value_eur", 0)
                
                losers.append({
                    "name": mover["name"],
                    "change_eur": round(mover["change_eur"], 2),
                    "change_pct": round((mover["change_eur"] / snapshot_val * 100) if snapshot_val > 0 else 0, 2),
                    "current_value_eur": round(current_val, 2),
                    "snapshot_value_eur": round(snapshot_val, 2),
                    "category": current_asset.get("category", "Unknown")
                })
        
        # 6. Calculate time since snapshot
        snapshot_time = datetime.fromisoformat(latest_snapshot["timestamp"])
        current_time = datetime.now(timezone.utc)
        days_ago = (current_time - snapshot_time).days
        
        # 7. Portfolio value comparison
        current_total = current_live_snapshot.get("total_value_eur", 0)
        snapshot_total = latest_snapshot.get("total_value_eur", 0)
        value_change = current_total - snapshot_total
        value_change_pct = (value_change / snapshot_total * 100) if snapshot_total > 0 else 0
        
        return {
            "success": True,
            "data": {
                "current_status": {
                    "total_value_eur": round(current_total, 2),
                    "asset_count": len(current_normalized),
                    "source": "google_sheets",
                    "timestamp": current_live_snapshot.get("timestamp")
                },
                "snapshot_comparison": {
                    "snapshot_date": latest_snapshot.get("timestamp"),
                    "snapshot_value_eur": round(snapshot_total, 2),
                    "days_ago": days_ago,
                    "value_change": {
                        "eur": round(value_change, 2),
                        "percentage": round(value_change_pct, 2),
                        "direction": "up" if value_change >= 0 else "down"
                    }
                },
                "winners": winners,
                "losers": losers,
                "summary": {
                    "new_positions": len(comparison.get("new_positions", [])),
                    "sold_positions": len(comparison.get("sold_positions", []))
                }
            },
            "metadata": {
                "timestamp": current_time.isoformat(),
                "source": "investment-mcp",
                "comparison": "live_vs_snapshot",
                "data_source_current": "google_sheets_live",
                "data_source_snapshot": "storage"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to perform quick analysis: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def get_winners_losers_json(limit: int = 5) -> Dict[str, Any]:
    """
    Compare last two snapshots (historical comparison).
    
    Different from quick_analysis:
    - Compares snapshot N vs snapshot N-1
    - Does NOT fetch live data
    - Faster (no API calls)
    
    Args:
        limit: Number of top/bottom movers (default: 5)
    
    Returns:
        dict: Winners/losers between last 2 snapshots
    """
    try:
        all_snapshots = storage.get_all_snapshots()
        
        if len(all_snapshots) < 2:
            return {
                "success": False,
                "error": "Need at least 2 snapshots for comparison. Run portfolio_analysis() to create snapshots.",
                "data": None
            }
        
        current = all_snapshots[-1]
        previous = all_snapshots[-2]
        
        # Load transactions for comparison
        transactions_data = storage.get_transactions()
        sell_transactions = transactions_data.get("sell_transactions", [])
        buy_transactions = transactions_data.get("buy_transactions", [])
        
        # Perform comparison
        report = analysis.compare_snapshots(
            current,
            previous,
            sell_transactions,
            buy_transactions
        )
        
        # Extract and enrich winners data
        winners = []
        for mover in report.get("top_movers", [])[:limit]:
            asset = next(
                (a for a in current.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            prev_asset = next(
                (a for a in previous.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            
            if asset and prev_asset:
                current_val = asset.get("current_value_eur", 0)
                prev_val = prev_asset.get("current_value_eur", 0)
                
                winners.append({
                    "name": mover["name"],
                    "change_eur": round(mover["change_eur"], 2),
                    "change_pct": round((mover["change_eur"] / prev_val * 100) if prev_val > 0 else 0, 2),
                    "current_value_eur": round(current_val, 2),
                    "previous_value_eur": round(prev_val, 2),
                    "category": asset.get("category", "Unknown")
                })
        
        # Extract and enrich losers data
        losers = []
        for mover in report.get("bottom_movers", [])[:limit]:
            asset = next(
                (a for a in current.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            prev_asset = next(
                (a for a in previous.get("assets", []) if a["name"] == mover["name"]),
                None
            )
            
            if asset and prev_asset:
                current_val = asset.get("current_value_eur", 0)
                prev_val = prev_asset.get("current_value_eur", 0)
                
                losers.append({
                    "name": mover["name"],
                    "change_eur": round(mover["change_eur"], 2),
                    "change_pct": round((mover["change_eur"] / prev_val * 100) if prev_val > 0 else 0, 2),
                    "current_value_eur": round(current_val, 2),
                    "previous_value_eur": round(prev_val, 2),
                    "category": asset.get("category", "Unknown")
                })
        
        # Calculate time period
        from_time = datetime.fromisoformat(previous["timestamp"])
        to_time = datetime.fromisoformat(current["timestamp"])
        days_diff = (to_time - from_time).days
        
        return {
            "success": True,
            "data": {
                "comparison_period": {
                    "from": previous["timestamp"],
                    "to": current["timestamp"],
                    "days": days_diff
                },
                "portfolio_change": {
                    "value_eur": round(report["total_value_change_eur"], 2),
                    "percentage": round(report["total_value_change_percent"], 2),
                    "direction": "up" if report["total_value_change_eur"] >= 0 else "down"
                },
                "winners": winners,
                "losers": losers
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "investment-mcp",
                "comparison": "snapshot_vs_snapshot",
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get winners/losers: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def get_upcoming_events_json() -> Dict[str, Any]:
    """
    Get upcoming earnings reports for portfolio stocks.
    
    Returns:
        dict: Upcoming events with structure:
        {
            "success": true,
            "data": {
                "events": [...],
                "total_events": 8,
                "provider": "Yahoo Finance"
            }
        }
    """
    try:
        logger.info("Fetching upcoming events for portfolio...")
        
        # Fetch live portfolio data
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Get upcoming events
        result = events_tracker.get_portfolio_upcoming_events(normalized_data)
        
        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Failed to fetch upcoming events"),
                "data": None
            }
        
        return {
            "success": True,
            "data": {
                "events": result.get("events", []),
                "total_events": result.get("total_events", 0),
                "earnings_count": result.get("earnings_count", 0),
                "provider": result.get("provider", "Unknown")
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "investment-mcp",
                "data_source": result.get("provider", "Unknown").lower().replace(" ", "_")
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def get_insider_trades_portfolio_json() -> Dict[str, Any]:
    """
    Get insider trading activity for all portfolio stocks.
    
    Returns:
        dict: Insider trades organized by sentiment
    """
    try:
        logger.info("Fetching insider trades for portfolio...")
        
        # Fetch live portfolio data
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Get insider trades
        result = insider_trading.get_portfolio_insider_trades(normalized_data)
        
        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Failed to fetch insider trades"),
                "data": None
            }
        
        return {
            "success": True,
            "data": {
                "stocks_analyzed": result.get("stocks_analyzed", 0),
                "stocks_with_activity": result.get("stocks_with_activity", 0),
                "total_transactions": result.get("total_transactions", 0),
                "by_sentiment": result.get("by_sentiment", {}),
                "stocks_no_activity": result.get("stocks_no_activity", [])
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "investment-mcp",
                "data_source": "fintel_api"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get portfolio insider trades: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def get_insider_trades_ticker_json(ticker: str) -> Dict[str, Any]:
    """
    Get insider trading activity for specific ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
    
    Returns:
        dict: Insider trades for ticker
    """
    try:
        logger.info(f"Fetching insider trades for {ticker}...")
        
        # Validate ticker
        if not ticker or not ticker.strip():
            return {
                "success": False,
                "error": "Ticker symbol is required",
                "data": None
            }
        
        ticker = ticker.strip().upper()
        
        # Get insider trades
        result = insider_trading.get_insider_trades_for_ticker(ticker)
        
        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Failed to fetch insider trades"),
                "data": None
            }
        
        return {
            "success": True,
            "data": {
                "ticker": result.get("ticker", ticker),
                "trades": result.get("trades", []),
                "total_trades": result.get("total_trades", 0),
                "statistics": result.get("statistics", {}),
                "url": result.get("url", "")
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "investment-mcp",
                "data_source": "fintel_api"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get insider trades for {ticker}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": None
        }
