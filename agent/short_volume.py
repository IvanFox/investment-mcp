"""
Short Volume and Short Interest Tracking Module

This module provides functionality to track short selling activity using Fintel API.
It fetches daily short volume data, short interest metrics, and provides risk analysis
for individual stocks and entire portfolios.
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from statistics import mean

from .insider_trading import load_fintel_api_key, determine_country_code

logger = logging.getLogger(__name__)

FINTEL_BASE_URL = "https://api.fintel.io/api/v1"
REQUEST_TIMEOUT = 30
DEFAULT_LOOKBACK_DAYS = 30


def fetch_short_volume(
    ticker: str,
    api_key: str,
    days: int = DEFAULT_LOOKBACK_DAYS
) -> Dict[str, Any]:
    """
    Fetch short volume data for a specific ticker from Fintel API.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "WISE.L")
        api_key: Fintel API key
        days: Number of days of historical data to fetch
        
    Returns:
        dict: API response containing short volume data
        
    Raises:
        requests.RequestException: If API request fails
    """
    country = determine_country_code(ticker)
    clean_ticker = ticker.split('.')[0].lower()
    
    url = f"https://api.fintel.io/web/v/0.0/ss/{country}/{clean_ticker}"
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }
    
    try:
        logger.debug(f"Fetching short volume from Fintel: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched short volume for {ticker}")
        return data
        
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No short volume data found for {ticker}")
            return {"data": [], "symbol": ticker, "country": country}
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
        logger.error(f"Failed to fetch short volume for {ticker}: {e}")
        raise


def fetch_short_interest(ticker: str, api_key: str) -> Dict[str, Any]:
    """
    Fetch short interest data for a specific ticker from Fintel API.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "WISE.L")
        api_key: Fintel API key
        
    Returns:
        dict: API response containing short interest data
        
    Raises:
        requests.RequestException: If API request fails
    """
    country = determine_country_code(ticker)
    clean_ticker = ticker.split('.')[0]
    
    url = f"{FINTEL_BASE_URL}/shortInterest/{country}/{clean_ticker}"
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }
    
    try:
        logger.debug(f"Fetching short interest from Fintel: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched short interest for {ticker}")
        return data
        
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No short interest data found for {ticker}")
            return {"symbol": ticker, "country": country}
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
        logger.error(f"Failed to fetch short interest for {ticker}: {e}")
        raise


def calculate_short_metrics(short_volume_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate short volume metrics and trends.
    
    Args:
        short_volume_data: List of daily short volume records
        
    Returns:
        dict: Calculated metrics including averages and trends
    """
    if not short_volume_data:
        return {
            'avg_short_ratio': 0.0,
            'avg_7day': 0.0,
            'avg_30day': 0.0,
            'latest_short_ratio': 0.0,
            'trend': 'Unknown',
            'data_points': 0,
        }
    
    sorted_data = sorted(short_volume_data, key=lambda x: x.get('marketDate', ''), reverse=True)
    
    short_ratios = [d.get('shortVolumeRatio', 0) * 100 for d in sorted_data if d.get('shortVolumeRatio') is not None]
    
    if not short_ratios:
        return {
            'avg_short_ratio': 0.0,
            'avg_7day': 0.0,
            'avg_30day': 0.0,
            'latest_short_ratio': 0.0,
            'trend': 'Unknown',
            'data_points': 0,
        }
    
    latest_short_ratio = short_ratios[0] if short_ratios else 0.0
    avg_7day = mean(short_ratios[:7]) if len(short_ratios) >= 7 else mean(short_ratios)
    avg_30day = mean(short_ratios[:30]) if len(short_ratios) >= 30 else mean(short_ratios)
    
    if len(short_ratios) >= 7:
        recent_avg = mean(short_ratios[:7])
        older_avg = mean(short_ratios[7:14]) if len(short_ratios) >= 14 else avg_30day
        
        if recent_avg > older_avg * 1.1:
            trend = 'Increasing ↗️'
        elif recent_avg < older_avg * 0.9:
            trend = 'Decreasing ↘️'
        else:
            trend = 'Stable ↔️'
    else:
        trend = 'Insufficient Data'
    
    return {
        'avg_short_ratio': mean(short_ratios),
        'avg_7day': avg_7day,
        'avg_30day': avg_30day,
        'latest_short_ratio': latest_short_ratio,
        'latest_date': sorted_data[0].get('marketDate', 'Unknown'),
        'trend': trend,
        'data_points': len(short_ratios),
    }


def analyze_short_risk(
    short_percent_float: Optional[float] = None,
    avg_short_ratio: Optional[float] = None,
    days_to_cover: Optional[float] = None
) -> Dict[str, str]:
    """
    Analyze short squeeze risk based on multiple factors.
    
    Args:
        short_percent_float: Short interest as % of float
        avg_short_ratio: Average short volume ratio (%)
        days_to_cover: Days to cover ratio
        
    Returns:
        dict: Risk level and description
    """
    score = 0
    factors = []
    
    if short_percent_float is not None:
        if short_percent_float > 20:
            score += 3
            factors.append(f"High short interest ({short_percent_float:.1f}% of float)")
        elif short_percent_float > 10:
            score += 2
            factors.append(f"Moderate short interest ({short_percent_float:.1f}% of float)")
        elif short_percent_float > 5:
            score += 1
            factors.append(f"Low-moderate short interest ({short_percent_float:.1f}% of float)")
    
    if days_to_cover is not None:
        if days_to_cover > 5:
            score += 2
            factors.append(f"High days to cover ({days_to_cover:.1f} days)")
        elif days_to_cover > 3:
            score += 1
            factors.append(f"Moderate days to cover ({days_to_cover:.1f} days)")
    
    if avg_short_ratio is not None:
        if avg_short_ratio > 40:
            score += 2
            factors.append(f"High short volume ratio ({avg_short_ratio:.1f}%)")
        elif avg_short_ratio > 30:
            score += 1
            factors.append(f"Moderate short volume ratio ({avg_short_ratio:.1f}%)")
    
    if score >= 5:
        risk_level = "High"
        risk_emoji = "🔴"
        description = "Short Squeeze Potential"
    elif score >= 3:
        risk_level = "Medium"
        risk_emoji = "🟡"
        description = "Moderate Short Pressure"
    else:
        risk_level = "Low"
        risk_emoji = "🟢"
        description = "Normal Short Activity"
    
    return {
        'risk_level': risk_level,
        'risk_emoji': risk_emoji,
        'description': description,
        'score': score,
        'factors': factors,
    }


def get_short_volume_for_ticker(ticker: str, days: int = DEFAULT_LOOKBACK_DAYS) -> Dict[str, Any]:
    """
    Get comprehensive short volume analysis for a ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "WISE.L")
        days: Number of days to look back (default: 30)
        
    Returns:
        dict: Complete short volume analysis with metrics and risk assessment
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
        short_volume_data = fetch_short_volume(ticker, api_key, days)
        
        volume_records = short_volume_data.get('data', [])
        
        if not volume_records:
            return {
                'success': True,
                'ticker': ticker,
                'data': [],
                'metrics': {},
                'message': f'No short volume data available for {ticker}',
            }
        
        metrics = calculate_short_metrics(volume_records)
        
        try:
            short_interest_data = fetch_short_interest(ticker, api_key)
            short_percent_float = short_interest_data.get('shortPercentOfFloat')
            if short_percent_float is not None:
                short_percent_float = short_percent_float * 100
            days_to_cover = short_interest_data.get('daysToCover')
        except Exception as e:
            logger.warning(f"Could not fetch short interest for {ticker}: {e}")
            short_interest_data = {}
            short_percent_float = None
            days_to_cover = None
        
        risk_analysis = analyze_short_risk(
            short_percent_float=short_percent_float,
            avg_short_ratio=metrics.get('avg_short_ratio'),
            days_to_cover=days_to_cover
        )
        
        return {
            'success': True,
            'ticker': ticker,
            'data': volume_records,
            'metrics': metrics,
            'short_interest': short_interest_data,
            'risk_analysis': risk_analysis,
            'as_of': datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get short volume for {ticker}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'ticker': ticker,
        }


def get_portfolio_short_analysis(portfolio_assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get short volume analysis for all portfolio stocks.
    
    Args:
        portfolio_assets: List of normalized asset dictionaries from sheets
        
    Returns:
        dict: Portfolio-wide short analysis organized by risk level
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
        logger.info(f"Fetching short volume for {ticker} ({asset_name})...")
        result = get_short_volume_for_ticker(ticker)
        
        if result.get('success') and result.get('metrics', {}).get('data_points', 0) > 0:
            all_results[ticker] = {
                'asset_name': asset_name,
                'data': result,
            }
        else:
            logger.warning(f"No short volume data for {ticker}: {result.get('message', 'Unknown')}")
    
    high_risk_stocks = []
    medium_risk_stocks = []
    low_risk_stocks = []
    stocks_no_data = []
    
    total_short_ratios = []
    
    for ticker, result_data in all_results.items():
        data = result_data['data']
        metrics = data.get('metrics', {})
        risk_analysis = data.get('risk_analysis', {})
        
        avg_short_ratio = metrics.get('avg_short_ratio', 0)
        if avg_short_ratio > 0:
            total_short_ratios.append(avg_short_ratio)
        
        stock_summary = {
            'ticker': ticker,
            'asset_name': result_data['asset_name'],
            'metrics': metrics,
            'risk_analysis': risk_analysis,
            'short_interest': data.get('short_interest', {}),
        }
        
        risk_level = risk_analysis.get('risk_level', 'Low')
        
        if risk_level == 'High':
            high_risk_stocks.append(stock_summary)
        elif risk_level == 'Medium':
            medium_risk_stocks.append(stock_summary)
        else:
            low_risk_stocks.append(stock_summary)
    
    for ticker, asset_name in ticker_to_asset.items():
        if ticker not in all_results:
            stocks_no_data.append(ticker)
    
    high_risk_stocks.sort(key=lambda x: x['risk_analysis'].get('score', 0), reverse=True)
    medium_risk_stocks.sort(key=lambda x: x['risk_analysis'].get('score', 0), reverse=True)
    
    avg_portfolio_short_ratio = mean(total_short_ratios) if total_short_ratios else 0.0
    
    return {
        'success': True,
        'stocks_analyzed': len(ticker_to_asset),
        'stocks_with_data': len(all_results),
        'avg_short_ratio': avg_portfolio_short_ratio,
        'high_risk_count': len(high_risk_stocks),
        'medium_risk_count': len(medium_risk_stocks),
        'low_risk_count': len(low_risk_stocks),
        'by_risk': {
            'high': high_risk_stocks,
            'medium': medium_risk_stocks,
            'low': low_risk_stocks,
        },
        'stocks_no_data': stocks_no_data,
        'as_of': datetime.now(timezone.utc).isoformat(),
    }
