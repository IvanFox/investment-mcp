"""
Events Tracker Module for Earnings Calendar

This module fetches earnings event data from Alpha Vantage API
and filters/sorts events for portfolio stocks.
"""

import json
import subprocess
import logging
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
DAYS_THRESHOLD = 60


def load_alpha_vantage_api_key() -> str:
    """
    Load Alpha Vantage API key from macOS Keychain.

    Returns:
        str: Alpha Vantage API key

    Raises:
        ValueError: If API key cannot be retrieved from keychain
    """
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                "mcp-portfolio-agent",
                "-s",
                "alpha-vantage-api-key",
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        api_key = result.stdout.strip()
        if not api_key:
            raise ValueError("API key is empty")
        logger.info("Successfully loaded Alpha Vantage API key from keychain")
        return api_key
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Failed to retrieve Alpha Vantage API key from keychain: {e.stderr}"
        )
    except Exception as e:
        raise ValueError(f"Failed to load Alpha Vantage API key: {e}")


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


def _parse_csv_response(csv_text: str) -> List[Dict[str, Any]]:
    """
    Parse CSV response from Alpha Vantage API.

    Args:
        csv_text: CSV formatted response text

    Returns:
        list: List of dictionaries parsed from CSV
    """
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        return list(reader) if reader else []
    except Exception as e:
        logger.error(f"Failed to parse CSV response: {e}")
        return []


def fetch_earnings_calendar(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch earnings calendar data from Alpha Vantage.

    Args:
        api_key: Alpha Vantage API key

    Returns:
        list: List of earnings events

    Raises:
        requests.RequestException: If API request fails
    """
    try:
        params = {
            "function": "EARNINGS_CALENDAR",
            "apikey": api_key,
            "horizon": "12month",
        }

        logger.debug(f"Fetching earnings calendar from Alpha Vantage with params: {params}")
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        logger.debug(f"Response status: {response.status_code}, Content-Type: {response.headers.get('content-type')}, Length: {len(response.text)}")

        if not response.text or len(response.text.strip()) == 0:
            logger.warning("Empty response from Alpha Vantage API for earnings calendar")
            return []

        try:
            data = response.json()
            logger.debug(f"Parsed JSON response with keys: {list(data.keys())}")
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage API rate limit: {data['Note']}")
                return []
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return []
            earnings_data = data.get("data", [])
            logger.info(f"Successfully fetched {len(earnings_data)} earnings events (JSON format)")
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse JSON response, attempting CSV parse: {e}")
            earnings_data = _parse_csv_response(response.text)
            logger.info(f"Successfully fetched {len(earnings_data)} earnings events (CSV format)")

        return earnings_data

    except requests.RequestException as e:
        logger.error(f"Failed to fetch earnings calendar: {e}")
        raise


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string from API response.

    Args:
        date_str: Date string in various formats

    Returns:
        datetime: Parsed datetime or None if parsing fails
    """
    if not date_str:
        return None

    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d %b %Y"]:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def filter_upcoming_events(
    events: List[Dict[str, Any]], date_field: str = "reportDate"
) -> List[Dict[str, Any]]:
    """
    Filter events that are within the next 2 months.

    Args:
        events: List of event dictionaries
        date_field: Field name containing the date

    Returns:
        list: Filtered events within 2-month window
    """
    now = datetime.now(timezone.utc)
    threshold_date = now + timedelta(days=DAYS_THRESHOLD)

    filtered_events = []

    for event in events:
        date_str = event.get(date_field, "")
        event_date = parse_date(date_str)

        if event_date is None:
            continue

        if now <= event_date <= threshold_date:
            days_until = (event_date - now).days
            event_copy = event.copy()
            event_copy["days_until"] = days_until
            event_copy["parsed_date"] = event_date
            filtered_events.append(event_copy)

    return filtered_events


def sort_events_chronologically(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Sort events chronologically by date.

    Args:
        events: List of event dictionaries

    Returns:
        list: Events sorted by date (earliest first)
    """
    return sorted(events, key=lambda e: e.get("parsed_date", datetime.now(timezone.utc)))


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
        ValueError: If unmapped stocks are found or API key is missing
    """
    try:
        api_key = load_alpha_vantage_api_key()
    except ValueError as e:
        return {
            "success": False,
            "error": f"Alpha Vantage API Key Error: {str(e)}",
            "help": "Please store your Alpha Vantage API key in keychain using setup_alpha_vantage.sh",
        }

    unmapped_stocks = []
    ticker_to_asset = {}
    skipped_assets = []

    SKIP_CATEGORIES = {"Bonds", "Pension", "Cash"}

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
        logger.info(f"Skipped {len(skipped_assets)} assets (bonds/pensions/cash): {', '.join(skipped_assets[:5])}{'...' if len(skipped_assets) > 5 else ''}")

    if unmapped_stocks:
        return {
            "success": False,
            "error": "Unmapped stocks found",
            "unmapped_stocks": unmapped_stocks,
            "action": "Please update ticker_mapping.json with the missing stock mappings",
        }

    try:
        earnings_events = fetch_earnings_calendar(api_key)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch earnings calendar from Alpha Vantage: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to fetch earnings data: {str(e)}",
        }

    earnings_upcoming = filter_upcoming_events(earnings_events, "reportDate")
    earnings_upcoming = sort_events_chronologically(earnings_upcoming)

    portfolio_tickers = set(ticker_to_asset.keys())
    portfolio_earnings = [
        e for e in earnings_upcoming if e.get("symbol") in portfolio_tickers
    ]

    tickers_with_no_events = portfolio_tickers - {
        e.get("symbol") for e in portfolio_earnings
    }

    if tickers_with_no_events:
        logger.debug(
            f"No upcoming events found for tickers: {', '.join(sorted(tickers_with_no_events))}"
        )

    all_events = []

    for earning in portfolio_earnings:
        try:
            all_events.append(
                {
                    "type": "Earnings Report",
                    "ticker": earning.get("symbol"),
                    "company_name": ticker_to_asset.get(earning.get("symbol"), ""),
                    "date": earning.get("reportDate"),
                    "days_until": earning.get("days_until"),
                    "report_date": earning.get("reportDate"),
                    "estimate": earning.get("estimate"),
                }
            )
        except Exception as e:
            logger.error(
                f"Error processing earnings event for {earning.get('symbol')}: {str(e)}"
            )
            continue

    all_events = sort_events_chronologically(all_events)

    return {
        "success": True,
        "events": all_events,
        "total_events": len(all_events),
        "earnings_count": len(portfolio_earnings),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
