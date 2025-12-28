"""
Insider Trading Module for Fintel API Integration

This module fetches insider trading data from Fintel Web Data API
and provides analysis of insider activities for portfolio stocks.
"""

import json
import subprocess
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

FINTEL_BASE_URL = "https://api.fintel.io/web/v/0.0/n"
DAYS_THRESHOLD = 90
REQUEST_TIMEOUT = 30


def load_fintel_api_key() -> str:
    """
    Load Fintel API key from macOS Keychain.
    
    Returns:
        str: Fintel API key
        
    Raises:
        ValueError: If API key cannot be retrieved from keychain
    """
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-a",
                "mcp-portfolio-agent",
                "-s",
                "fintel-api-key",
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        api_key = result.stdout.strip()
        if not api_key:
            raise ValueError("API key is empty")
        logger.info("Successfully loaded Fintel API key from keychain")
        return api_key
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Failed to retrieve Fintel API key from keychain: {e.stderr}. "
            f"Please run ./setup_fintel.sh with your API key."
        )
    except Exception as e:
        raise ValueError(f"Failed to load Fintel API key: {e}")


def determine_country_code(ticker: str) -> str:
    """
    Determine country code from ticker symbol.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "WISE.L", "ASML.AS")
        
    Returns:
        str: Country code for API request (e.g., "us", "uk", "nl")
    """
    if '.' in ticker:
        parts = ticker.split('.')
        exchange = parts[-1].upper()
        
        exchange_map = {
            'L': 'uk',
            'AS': 'nl',
            'PA': 'fr',
            'DE': 'de',
            'SW': 'ch',
            'TO': 'ca',
        }
        return exchange_map.get(exchange, 'us')
    
    return 'us'


def fetch_insider_trades(
    ticker: str, 
    api_key: str,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch insider trading data for a specific ticker from Fintel API.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        api_key: Fintel API key
        country: Country code (auto-detected if not provided)
        
    Returns:
        dict: API response containing insider trades data
        
    Raises:
        requests.RequestException: If API request fails
    """
    if country is None:
        country = determine_country_code(ticker)
    
    clean_ticker = ticker.split('.')[0]
    
    url = f"{FINTEL_BASE_URL}/{country}/{clean_ticker}"
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }
    
    try:
        logger.debug(f"Fetching insider trades from Fintel: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched insider trades for {ticker}")
        return data
        
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No insider trading data found for {ticker}")
            return {"entries": [], "symbol": ticker, "url": "https://fintel.io"}
        elif e.response.status_code == 401:
            raise ValueError(
                "Invalid Fintel API key. Please check your API key and run ./setup_fintel.sh"
            )
        elif e.response.status_code == 429:
            raise ValueError(
                "Fintel API rate limit exceeded. Please wait before making more requests."
            )
        else:
            raise
    except requests.RequestException as e:
        logger.error(f"Failed to fetch insider trades for {ticker}: {e}")
        raise


def parse_trade_date(date_str: str) -> Optional[datetime]:
    """
    Parse trade date string from Fintel API response.
    
    Args:
        date_str: Date string from API
        
    Returns:
        datetime: Parsed datetime or None if parsing fails
    """
    if not date_str:
        return None
        
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y%m%d"]:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
            
    logger.warning(f"Could not parse trade date: {date_str}")
    return None


def filter_trades_by_date(
    trades: List[Dict[str, Any]], 
    days: int = DAYS_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Filter trades to last N days.
    
    Args:
        trades: List of trade dictionaries
        days: Number of days to look back (default: 90)
        
    Returns:
        list: Filtered trades within time window
    """
    now = datetime.now(timezone.utc)
    threshold_date = now - timedelta(days=days)
    
    filtered_trades = []
    
    for trade in trades:
        trade_date_str = trade.get('transactionDate') or trade.get('fileDate') or trade.get('date')
        if trade_date_str is None:
            continue
        trade_date = parse_trade_date(trade_date_str)
        
        if trade_date is None:
            continue
            
        if trade_date >= threshold_date:
            trade_copy = trade.copy()
            trade_copy['parsed_date'] = trade_date.isoformat()
            trade_copy['days_ago'] = (now - trade_date).days
            filtered_trades.append(trade_copy)
    
    # Sort by the datetime object before conversion, or by the ISO string (both work)
    return sorted(filtered_trades, key=lambda t: t['parsed_date'], reverse=True)


def categorize_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Categorize trades into buys/sells and aggregate statistics.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        dict: Aggregated statistics
    """
    buys = []
    sells = []
    
    buy_volume = 0
    sell_volume = 0
    buy_value = 0.0
    sell_value = 0.0
    
    for trade in trades:
        transaction_code = (trade.get('code') or '').lower()
        shares = float(trade.get('shares', 0))
        value = abs(float(trade.get('value') or 0))
        
        is_buy = shares > 0 or any(keyword in transaction_code for keyword in ['buy', 'purchase', 'acquisition', 'optionex'])
        is_sell = shares < 0 or any(keyword in transaction_code for keyword in ['sale', 'sell', 'disposition'])
        
        if is_buy:
            buys.append(trade)
            buy_volume += abs(shares)
            buy_value += value
        elif is_sell:
            sells.append(trade)
            sell_volume += abs(shares)
            sell_value += value
    
    if sell_value > buy_value * 2:
        sentiment = "Bearish"
    elif buy_value > sell_value * 2:
        sentiment = "Bullish"
    else:
        sentiment = "Neutral"
    
    return {
        'total_buys': len(buys),
        'total_sells': len(sells),
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'buy_value_usd': buy_value,
        'sell_value_usd': sell_value,
        'net_sentiment': sentiment,
        'buys': buys,
        'sells': sells,
    }


def get_insider_trades_for_ticker(ticker: str) -> Dict[str, Any]:
    """
    Fetch and analyze insider trading data for any ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
        
    Returns:
        dict: Analysis results with trades and statistics, or error information
    """
    try:
        api_key = load_fintel_api_key()
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'help': 'Please run ./setup_fintel.sh with your Fintel API key',
        }
    
    try:
        data = fetch_insider_trades(ticker, api_key)
        
        all_trades = data.get('insiders', [])
        
        if not all_trades:
            return {
                'success': True,
                'ticker': ticker,
                'trades': [],
                'total_trades': 0,
                'message': f'No insider trading data available for {ticker}',
                'url': data.get('url', 'https://fintel.io'),
            }
        
        recent_trades = filter_trades_by_date(all_trades, DAYS_THRESHOLD)
        
        stats = categorize_trades(recent_trades)
        
        return {
            'success': True,
            'ticker': ticker,
            'trades': recent_trades,
            'total_trades': len(recent_trades),
            'statistics': stats,
            'url': data.get('url', 'https://fintel.io'),
            'as_of': datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get insider trades for {ticker}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'ticker': ticker,
        }


def get_portfolio_insider_trades(
    portfolio_assets: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Get insider trading data for all portfolio stocks.
    
    Args:
        portfolio_assets: List of normalized asset dictionaries from sheets
        
    Returns:
        dict: Organized insider trades or error information
    """
    from . import events_tracker
    
    try:
        api_key = load_fintel_api_key()
    except ValueError as e:
        return {
            'success': False,
            'error': f'Fintel API Key Error: {str(e)}',
            'help': 'Please run ./setup_fintel.sh with your Fintel API key',
        }
    
    unmapped_stocks = []
    ticker_to_asset = {}
    skipped_assets = []
    
    SKIP_CATEGORIES = {'Bonds', 'Pension', 'Cash', 'ETFs'}
    
    for asset in portfolio_assets:
        asset_name = asset.get('name', '')
        asset_category = asset.get('category', '')
        
        if asset_category in SKIP_CATEGORIES:
            skipped_assets.append(f"{asset_name} ({asset_category})")
            continue
        
        try:
            ticker = events_tracker.get_ticker_for_asset(asset_name)
            ticker_to_asset[ticker] = asset_name
        except ValueError as e:
            unmapped_stocks.append(str(e))
    
    if skipped_assets:
        logger.info(
            f"Skipped {len(skipped_assets)} assets (bonds/pensions/cash/ETFs): "
            f"{', '.join(skipped_assets[:5])}{'...' if len(skipped_assets) > 5 else ''}"
        )
    
    if unmapped_stocks:
        return {
            'success': False,
            'error': 'Unmapped stocks found',
            'unmapped_stocks': unmapped_stocks,
            'action': 'Please update ticker_mapping.json with missing stock mappings',
        }
    
    all_results = {}
    
    for ticker, asset_name in ticker_to_asset.items():
        logger.info(f"Fetching insider trades for {ticker} ({asset_name})...")
        result = get_insider_trades_for_ticker(ticker)
        
        if result.get('success'):
            all_results[ticker] = {
                'asset_name': asset_name,
                'data': result,
            }
        else:
            logger.warning(f"Failed to fetch insider trades for {ticker}: {result.get('error')}")
    
    bullish_stocks = []
    neutral_stocks = []
    bearish_stocks = []
    stocks_no_activity = []
    total_transactions = 0
    
    for ticker, result_data in all_results.items():
        data = result_data['data']
        total_trades = data.get('total_trades', 0)
        
        if total_trades == 0:
            stocks_no_activity.append(ticker)
            continue
        
        total_transactions += total_trades
        stats = data.get('statistics', {})
        sentiment = stats.get('net_sentiment', 'Neutral')
        
        stock_summary = {
            'ticker': ticker,
            'asset_name': result_data['asset_name'],
            'total_trades': total_trades,
            'statistics': stats,
        }
        
        if sentiment == 'Bullish':
            bullish_stocks.append(stock_summary)
        elif sentiment == 'Bearish':
            bearish_stocks.append(stock_summary)
        else:
            neutral_stocks.append(stock_summary)
    
    return {
        'success': True,
        'stocks_analyzed': len(ticker_to_asset),
        'stocks_with_activity': len(all_results) - len(stocks_no_activity),
        'total_transactions': total_transactions,
        'by_sentiment': {
            'Bullish': bullish_stocks,
            'Neutral': neutral_stocks,
            'Bearish': bearish_stocks,
        },
        'stocks_no_activity': stocks_no_activity,
        'as_of': datetime.now(timezone.utc).isoformat(),
    }
