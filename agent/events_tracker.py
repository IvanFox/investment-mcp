"""
Events Tracker Module for Earnings Calendar

This module fetches earnings event data using pluggable data providers.
Default provider is Yahoo Finance (free, no API key required).
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from .providers.yahoo_earnings_provider import YahooEarningsProvider
from .earnings_models import EarningsEvent

logger = logging.getLogger(__name__)

DAYS_THRESHOLD = 60

# Default earnings data provider
_earnings_provider = None


def get_earnings_provider() -> YahooEarningsProvider:
    """
    Get the configured earnings data provider.
    
    Returns:
        YahooEarningsProvider: The earnings data provider instance
    """
    global _earnings_provider
    if _earnings_provider is None:
        _earnings_provider = YahooEarningsProvider()
        logger.info(f"Initialized earnings provider: {_earnings_provider.provider_name}")
    return _earnings_provider


def load_ticker_mapping() -> Dict[str, str]:
    """
    Load the ticker mapping from ticker_mapping.json file.

    Returns:
        dict: Mapping from asset names to ticker symbols

    Raises:
        FileNotFoundError: If ticker_mapping.json not found
        json.JSONDecodeError: If ticker_mapping.json is invalid
    """
    try:
        with open("ticker_mapping.json", "r") as f:
            mapping_data = json.load(f)
        mappings = mapping_data.get("mappings", {})
        return {k: v for k, v in mappings.items() if not k.startswith("_")}
    except FileNotFoundError:
        raise FileNotFoundError(
            "ticker_mapping.json not found. Please create it with stock mappings."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"ticker_mapping.json is invalid JSON: {e}")


def get_ticker_for_asset(asset_name: str) -> str:
    """
    Get the ticker symbol for a given asset name.

    Args:
        asset_name: Name of the asset as it appears in portfolio

    Returns:
        str: Ticker symbol for the asset

    Raises:
        ValueError: If asset name is not mapped
    """
    ticker_map = load_ticker_mapping()

    if asset_name not in ticker_map:
        raise ValueError(
            f"Stock '{asset_name}' is not mapped in ticker_mapping.json. "
            f"Please add a mapping for this stock to proceed. "
            f"Current mappings: {list(ticker_map.keys())}"
        )

    return ticker_map[asset_name]


def filter_upcoming_events(
    events: List[EarningsEvent], days_threshold: int = DAYS_THRESHOLD
) -> List[EarningsEvent]:
    """
    Filter events that are within the specified time threshold.

    Args:
        events: List of EarningsEvent objects
        days_threshold: Number of days to look ahead (default: 60)

    Returns:
        list: Filtered events within the time window
    """
    now = datetime.now(timezone.utc)
    threshold_date = now + timedelta(days=days_threshold)

    filtered_events = []

    for event in events:
        # Ensure event date is timezone-aware
        event_date = event.report_date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        
        if now <= event_date <= threshold_date:
            filtered_events.append(event)

    return filtered_events


def sort_events_chronologically(events: List[EarningsEvent]) -> List[EarningsEvent]:
    """
    Sort events chronologically by date.

    Args:
        events: List of EarningsEvent objects

    Returns:
        list: Events sorted by date (earliest first)
    """
    return sorted(events, key=lambda e: e.report_date)


def get_earnings_for_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get next earnings date for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
    
    Returns:
        dict: Earnings event information or error details
    """
    try:
        provider = get_earnings_provider()
        event = provider.fetch_earnings_for_ticker(ticker)
        
        if event is None:
            return {
                "success": False,
                "error": f"No earnings date found for {ticker}",
                "ticker": ticker,
            }
        
        now = datetime.now(timezone.utc)
        days_until = event.days_until(now)
        
        return {
            "success": True,
            "ticker": event.ticker,
            "company_name": event.company_name,
            "report_date": event.report_date.isoformat(),
            "days_until": days_until,
            "estimate": event.estimate,
            "fiscal_period": event.fiscal_period,
            "source": event.source,
            "as_of": now.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch earnings for {ticker}: {e}")
        return {
            "success": False,
            "error": f"Failed to fetch earnings data: {str(e)}",
            "ticker": ticker,
        }


def get_portfolio_upcoming_events(
    portfolio_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Get upcoming earnings events for all portfolio assets.

    Args:
        portfolio_assets: List of normalized asset dictionaries from sheets

    Returns:
        dict: Organized upcoming events or error information

    Raises:
        ValueError: If unmapped stocks are found
    """
    unmapped_stocks = []
    ticker_to_asset = {}
    skipped_assets = []

    SKIP_CATEGORIES = {"Bonds", "Pension", "Cash", "ETFs"}

    for asset in portfolio_assets:
        asset_name = asset.get("name", "")
        asset_category = asset.get("category", "")

        if asset_category in SKIP_CATEGORIES:
            skipped_assets.append(f"{asset_name} ({asset_category})")
            continue

        try:
            ticker = get_ticker_for_asset(asset_name)
            ticker_to_asset[ticker] = asset_name
        except ValueError as e:
            unmapped_stocks.append(str(e))

    if skipped_assets:
        logger.info(f"Skipped {len(skipped_assets)} assets (bonds/ETFs/pensions/cash): {', '.join(skipped_assets[:5])}{'...' if len(skipped_assets) > 5 else ''}")

    if unmapped_stocks:
        return {
            "success": False,
            "error": "Unmapped stocks found",
            "unmapped_stocks": unmapped_stocks,
            "action": "Please update ticker_mapping.json with the missing stock mappings",
        }

    try:
        provider = get_earnings_provider()
        portfolio_tickers = list(ticker_to_asset.keys())
        
        logger.info(f"Fetching earnings for {len(portfolio_tickers)} portfolio stocks from {provider.provider_name}...")
        
        # Fetch earnings for all portfolio tickers
        earnings_events = provider.fetch_earnings_for_tickers(
            portfolio_tickers, 
            horizon_months=2  # 2 months = 60 days
        )
        
        logger.info(f"Fetched {len(earnings_events)} earnings events from {provider.provider_name}")
        
    except Exception as e:
        logger.error(f"Failed to fetch earnings calendar: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to fetch earnings data: {str(e)}",
        }

    # Filter to only upcoming events within threshold
    earnings_upcoming = filter_upcoming_events(earnings_events, DAYS_THRESHOLD)
    earnings_upcoming = sort_events_chronologically(earnings_upcoming)

    tickers_with_events = {e.ticker for e in earnings_upcoming}
    tickers_with_no_events = set(portfolio_tickers) - tickers_with_events

    if tickers_with_no_events:
        logger.debug(
            f"No upcoming events found for tickers: {', '.join(sorted(tickers_with_no_events))}"
        )

    # Convert EarningsEvent objects to dictionaries
    all_events = []
    now = datetime.now(timezone.utc)

    for event in earnings_upcoming:
        try:
            days_until = event.days_until(now)
            all_events.append(
                {
                    "type": "Earnings Report",
                    "ticker": event.ticker,
                    "company_name": event.company_name,
                    "date": event.report_date.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "report_date": event.report_date.strftime("%Y-%m-%d"),
                    "estimate": event.estimate,
                    "source": event.source,
                }
            )
        except Exception as e:
            logger.error(
                f"Error processing earnings event for {event.ticker}: {str(e)}"
            )
            continue

    return {
        "success": True,
        "events": all_events,
        "total_events": len(all_events),
        "earnings_count": len(all_events),
        "provider": provider.provider_name,
        "as_of": now.isoformat(),
    }
