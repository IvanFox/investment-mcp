"""
Portfolio Risk Analysis Module

Calculates comprehensive risk metrics including beta, VaR, 
concentration risk, correlations, and volatility.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import subprocess

import numpy as np
import pandas as pd
from scipy import stats
import requests

logger = logging.getLogger(__name__)

CACHE_DIR = "cache"
CACHE_DURATION_HOURS = 24
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
MARKET_BENCHMARK_TICKER = "SPY"
TRADING_DAYS_PER_YEAR = 252
API_RATE_LIMIT_DELAY = 12


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
                "/usr/bin/security",
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
        return api_key
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Failed to retrieve Alpha Vantage API key from keychain: {e.stderr}"
        )
    except Exception as e:
        raise ValueError(f"Failed to load Alpha Vantage API key: {e}")


def ensure_cache_dir() -> None:
    """
    Ensure cache directory exists.
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")


def get_cache_path(ticker: str) -> str:
    """
    Get cache file path for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        str: Path to cache file
    """
    ensure_cache_dir()
    return os.path.join(CACHE_DIR, f"{ticker}_prices.json")


def is_cache_valid(cache_path: str) -> bool:
    """
    Check if cache file exists and is within valid duration.

    Args:
        cache_path: Path to cache file

    Returns:
        bool: True if cache is valid
    """
    if not os.path.exists(cache_path):
        return False
    
    try:
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path), tz=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - file_time).total_seconds() / 3600
        return age_hours < CACHE_DURATION_HOURS
    except Exception as e:
        logger.warning(f"Error checking cache validity: {e}")
        return False


def fetch_historical_prices(ticker: str, api_key: str, lookback_days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch historical daily prices for a ticker from Alpha Vantage.
    Uses caching to avoid redundant API calls.

    Args:
        ticker: Stock ticker symbol
        api_key: Alpha Vantage API key
        lookback_days: Number of days of history to fetch

    Returns:
        DataFrame with columns: date, close, or None if fetch fails
    """
    cache_path = get_cache_path(ticker)
    
    if is_cache_valid(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            df = pd.DataFrame(cached_data)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"Loaded cached prices for {ticker}")
            return df
        except Exception as e:
            logger.warning(f"Failed to load cache for {ticker}: {e}")
    
    try:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "full",
            "apikey": api_key,
        }
        
        logger.info(f"Fetching historical prices for {ticker} from Alpha Vantage...")
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if "Error Message" in data:
            logger.error(f"Alpha Vantage error for {ticker}: {data['Error Message']}")
            return None
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage rate limit for {ticker}: {data['Note']}")
            return None
        
        time_series = data.get("Time Series (Daily)", {})
        
        if not time_series:
            logger.warning(f"No time series data returned for {ticker}")
            return None
        
        prices = []
        for date_str, values in time_series.items():
            prices.append({
                "date": date_str,
                "close": float(values.get("5. adjusted close", values.get("4. close", 0)))
            })
        
        df = pd.DataFrame(prices)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        df = df[df['date'] >= cutoff_date.replace(tzinfo=None)]
        
        try:
            with open(cache_path, 'w') as f:
                cache_data = df.to_dict('records')
                for record in cache_data:
                    record['date'] = record['date'].isoformat()
                json.dump(cache_data, f, indent=2)
            logger.info(f"Cached {len(df)} days of prices for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to cache prices for {ticker}: {e}")
        
        time.sleep(API_RATE_LIMIT_DELAY)
        
        return df
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch prices for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching prices for {ticker}: {e}")
        return None


def calculate_returns(prices: pd.DataFrame) -> pd.Series:
    """
    Calculate daily returns from price series.

    Args:
        prices: DataFrame with 'close' column

    Returns:
        Series of daily returns (percentage change)
    """
    if prices is None or len(prices) < 2:
        return pd.Series(dtype=float)
    
    returns = prices['close'].pct_change().dropna()
    return returns


def calculate_portfolio_beta(portfolio_returns: pd.Series, market_returns: pd.Series) -> Optional[float]:
    """
    Calculate portfolio beta relative to market benchmark.

    Args:
        portfolio_returns: Series of portfolio daily returns
        market_returns: Series of market daily returns

    Returns:
        float: Portfolio beta, or None if calculation fails
    """
    if len(portfolio_returns) < 30 or len(market_returns) < 30:
        logger.warning("Insufficient data for beta calculation (need at least 30 days)")
        return None
    
    try:
        aligned_portfolio, aligned_market = portfolio_returns.align(market_returns, join='inner')
        
        if len(aligned_portfolio) < 30:
            logger.warning("Insufficient aligned data for beta calculation")
            return None
        
        covariance = aligned_portfolio.cov(aligned_market)
        market_variance = aligned_market.var()
        
        if market_variance == 0:
            logger.warning("Market variance is zero, cannot calculate beta")
            return None
        
        beta = covariance / market_variance
        return float(beta)
        
    except Exception as e:
        logger.error(f"Error calculating beta: {e}")
        return None


def calculate_var_historical(returns: pd.Series, confidence_level: float = 0.95) -> Optional[float]:
    """
    Calculate Value at Risk using historical method.

    Args:
        returns: Series of daily returns
        confidence_level: Confidence level (0.95 for 95%, 0.99 for 99%)

    Returns:
        float: VaR as a negative percentage, or None if calculation fails
    """
    if len(returns) < 30:
        logger.warning("Insufficient data for VaR calculation")
        return None
    
    try:
        var = np.percentile(returns, (1 - confidence_level) * 100)
        return float(var)
    except Exception as e:
        logger.error(f"Error calculating historical VaR: {e}")
        return None


def calculate_var_parametric(returns: pd.Series, confidence_level: float = 0.95) -> Optional[float]:
    """
    Calculate Value at Risk using parametric method (assumes normal distribution).

    Args:
        returns: Series of daily returns
        confidence_level: Confidence level (0.95 for 95%, 0.99 for 99%)

    Returns:
        float: VaR as a negative percentage, or None if calculation fails
    """
    if len(returns) < 30:
        logger.warning("Insufficient data for parametric VaR calculation")
        return None
    
    try:
        mean = returns.mean()
        std = returns.std()
        z_score = stats.norm.ppf(1 - confidence_level)
        var = mean + z_score * std
        return float(var)
    except Exception as e:
        logger.error(f"Error calculating parametric VaR: {e}")
        return None


def calculate_concentration_risk(assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate concentration risk metrics including HHI.

    Args:
        assets: List of portfolio assets with current_value_eur

    Returns:
        dict: Concentration risk metrics
    """
    try:
        total_value = sum(asset.get('current_value_eur', 0) for asset in assets)
        
        if total_value == 0:
            return {
                "hhi": 0.0,
                "largest_position_pct": 0.0,
                "top_5_concentration_pct": 0.0,
                "num_positions": len(assets),
                "largest_position_name": None,
            }
        
        weights = []
        asset_values = []
        
        for asset in assets:
            value = asset.get('current_value_eur', 0)
            if value > 0:
                weight = value / total_value
                weights.append(weight)
                asset_values.append({
                    "name": asset.get('name', 'Unknown'),
                    "value": value,
                    "weight": weight
                })
        
        asset_values.sort(key=lambda x: x['weight'], reverse=True)
        
        hhi = sum(w ** 2 for w in weights)
        
        largest_position_pct = asset_values[0]['weight'] * 100 if asset_values else 0.0
        largest_position_name = asset_values[0]['name'] if asset_values else None
        
        top_5_concentration_pct = sum(av['weight'] for av in asset_values[:5]) * 100
        
        return {
            "hhi": round(hhi, 4),
            "largest_position_pct": round(largest_position_pct, 2),
            "top_5_concentration_pct": round(top_5_concentration_pct, 2),
            "num_positions": len(asset_values),
            "largest_position_name": largest_position_name,
            "top_holdings": [
                {"name": av['name'], "weight_pct": round(av['weight'] * 100, 2)}
                for av in asset_values[:5]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error calculating concentration risk: {e}")
        return {
            "hhi": 0.0,
            "error": str(e)
        }


def calculate_correlation_matrix(asset_returns: Dict[str, pd.Series]) -> Optional[pd.DataFrame]:
    """
    Calculate correlation matrix between asset returns.

    Args:
        asset_returns: Dictionary mapping asset names to return series

    Returns:
        DataFrame: Correlation matrix, or None if calculation fails
    """
    if len(asset_returns) < 2:
        logger.warning("Need at least 2 assets for correlation matrix")
        return None
    
    try:
        returns_df = pd.DataFrame(asset_returns)
        
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 30:
            logger.warning("Insufficient aligned data for correlation matrix")
            return None
        
        correlation_matrix = returns_df.corr()
        
        return correlation_matrix
        
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        return None


def analyze_sector_exposure(assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze portfolio exposure by sector/category and geography.

    Args:
        assets: List of portfolio assets

    Returns:
        dict: Exposure analysis by sector and geography
    """
    try:
        total_value = sum(asset.get('current_value_eur', 0) for asset in assets)
        
        if total_value == 0:
            return {"sectors": {}, "geography": {}, "total_value": 0}
        
        sectors = {}
        geography = {}
        
        for asset in assets:
            value = asset.get('current_value_eur', 0)
            if value <= 0:
                continue
            
            category = asset.get('category', 'Other')
            
            if category not in sectors:
                sectors[category] = {"value": 0, "percentage": 0, "count": 0}
            
            sectors[category]["value"] += value
            sectors[category]["count"] += 1
            
            ticker = asset.get('ticker', '')
            geo_region = _infer_geography(category, ticker)
            
            if geo_region not in geography:
                geography[geo_region] = {"value": 0, "percentage": 0, "count": 0}
            
            geography[geo_region]["value"] += value
            geography[geo_region]["count"] += 1
        
        for sector_data in sectors.values():
            sector_data["percentage"] = round((sector_data["value"] / total_value) * 100, 2)
            sector_data["value"] = round(sector_data["value"], 2)
        
        for geo_data in geography.values():
            geo_data["percentage"] = round((geo_data["value"] / total_value) * 100, 2)
            geo_data["value"] = round(geo_data["value"], 2)
        
        sectors = dict(sorted(sectors.items(), key=lambda x: x[1]["value"], reverse=True))
        geography = dict(sorted(geography.items(), key=lambda x: x[1]["value"], reverse=True))
        
        return {
            "sectors": sectors,
            "geography": geography,
            "total_value": round(total_value, 2)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing sector exposure: {e}")
        return {"error": str(e)}


def _infer_geography(category: str, ticker: str) -> str:
    """
    Infer geographic region from category and ticker.

    Args:
        category: Asset category
        ticker: Stock ticker symbol

    Returns:
        str: Geographic region
    """
    if category in ["Cash", "Pension", "Bonds"]:
        return "Other"
    
    if any(suffix in ticker for suffix in [".L", ".PA", ".DE", ".AS", ".MC", ".EE", ".TL", ".MI"]):
        return "Europe"
    
    if "ETF" in category or "VWCE" in ticker or "MEUD" in ticker:
        return "Global/ETF"
    
    return "United States"


def calculate_volatility_by_category(
    asset_returns: Dict[str, pd.Series], 
    assets: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate annualized volatility grouped by asset category.

    Args:
        asset_returns: Dictionary mapping asset names to return series
        assets: List of portfolio assets with category information

    Returns:
        dict: Volatility by category
    """
    try:
        category_returns = {}
        
        asset_category_map = {asset['name']: asset.get('category', 'Other') for asset in assets}
        
        for asset_name, returns in asset_returns.items():
            category = asset_category_map.get(asset_name, 'Other')
            
            if category not in category_returns:
                category_returns[category] = []
            
            category_returns[category].append(returns)
        
        volatility_by_category = {}
        
        for category, returns_list in category_returns.items():
            combined_returns = pd.concat(returns_list, axis=0)
            
            if len(combined_returns) > 0:
                daily_vol = combined_returns.std()
                annual_vol = daily_vol * np.sqrt(TRADING_DAYS_PER_YEAR)
                volatility_by_category[category] = round(float(annual_vol) * 100, 2)
        
        return volatility_by_category
        
    except Exception as e:
        logger.error(f"Error calculating volatility by category: {e}")
        return {}


def calculate_downside_metrics(returns: pd.Series, risk_free_rate: float = 0.02) -> Dict[str, Any]:
    """
    Calculate downside risk metrics.

    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default 2%)

    Returns:
        dict: Downside risk metrics
    """
    if len(returns) < 30:
        logger.warning("Insufficient data for downside metrics")
        return {}
    
    try:
        daily_rf_rate = risk_free_rate / TRADING_DAYS_PER_YEAR
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        
        excess_returns = returns - daily_rf_rate
        mean_excess_return = excess_returns.mean()
        
        sortino_ratio = 0
        if downside_std > 0:
            sortino_ratio = (mean_excess_return * TRADING_DAYS_PER_YEAR) / (downside_std * np.sqrt(TRADING_DAYS_PER_YEAR))
        
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        var_95 = calculate_var_historical(returns, 0.95)
        if var_95 is not None:
            losses_beyond_var = returns[returns <= var_95]
            cvar_95 = losses_beyond_var.mean() if len(losses_beyond_var) > 0 else var_95
        else:
            cvar_95 = None
        
        return {
            "sortino_ratio": round(float(sortino_ratio), 3),
            "max_drawdown_pct": round(float(max_drawdown) * 100, 2),
            "downside_deviation": round(float(downside_std) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100, 2),
            "cvar_95_pct": round(float(cvar_95) * 100, 2) if cvar_95 is not None else None,
        }
        
    except Exception as e:
        logger.error(f"Error calculating downside metrics: {e}")
        return {"error": str(e)}


def calculate_portfolio_returns(
    asset_returns: Dict[str, pd.Series],
    assets: List[Dict[str, Any]],
    total_value: float
) -> pd.Series:
    """
    Calculate portfolio returns based on weighted asset returns.

    Args:
        asset_returns: Dictionary mapping asset names to return series
        assets: List of portfolio assets
        total_value: Total portfolio value

    Returns:
        Series: Portfolio daily returns
    """
    try:
        asset_weights = {}
        for asset in assets:
            name = asset['name']
            value = asset.get('current_value_eur', 0)
            if name in asset_returns and value > 0:
                asset_weights[name] = value / total_value
        
        all_dates = set()
        for returns in asset_returns.values():
            all_dates.update(returns.index)
        
        all_dates = sorted(all_dates)
        
        portfolio_returns = pd.Series(0.0, index=all_dates)
        
        for asset_name, weight in asset_weights.items():
            if asset_name in asset_returns:
                returns = asset_returns[asset_name]
                portfolio_returns = portfolio_returns.add(returns * weight, fill_value=0)
        
        return portfolio_returns
        
    except Exception as e:
        logger.error(f"Error calculating portfolio returns: {e}")
        return pd.Series(dtype=float)


def analyze_portfolio_risk(portfolio_assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main orchestrator function that performs comprehensive risk analysis.

    Args:
        portfolio_assets: List of normalized asset dictionaries from portfolio snapshot

    Returns:
        dict: Complete risk analysis results
    """
    try:
        logger.info("Starting comprehensive portfolio risk analysis...")
        
        api_key = load_alpha_vantage_api_key()
        
        total_value = sum(asset.get('current_value_eur', 0) for asset in portfolio_assets)
        
        logger.info("Loading ticker mappings...")
        from . import events_tracker
        ticker_map = events_tracker.load_ticker_mapping()
        
        stock_assets = []
        for asset in portfolio_assets:
            category = asset.get('category', '')
            if category not in ['Cash', 'Pension', 'Bonds']:
                asset_name = asset.get('name', '')
                if asset_name in ticker_map:
                    asset['ticker'] = ticker_map[asset_name]
                    stock_assets.append(asset)
        
        logger.info(f"Analyzing {len(stock_assets)} stock positions out of {len(portfolio_assets)} total assets")
        
        logger.info("Fetching historical prices for stocks...")
        asset_prices = {}
        asset_returns = {}
        
        for i, asset in enumerate(stock_assets):
            ticker = asset.get('ticker')
            if not ticker:
                continue
            
            logger.info(f"Fetching prices for {ticker} ({i+1}/{len(stock_assets)})...")
            prices = fetch_historical_prices(ticker, api_key)
            
            if prices is not None and len(prices) > 0:
                asset_prices[asset['name']] = prices
                returns = calculate_returns(prices)
                if len(returns) > 0:
                    asset_returns[asset['name']] = returns
        
        logger.info(f"Successfully fetched data for {len(asset_returns)} assets")
        
        logger.info("Fetching market benchmark data...")
        market_prices = fetch_historical_prices(MARKET_BENCHMARK_TICKER, api_key)
        market_returns = calculate_returns(market_prices) if market_prices is not None else pd.Series(dtype=float)
        
        logger.info("Calculating concentration risk...")
        concentration = calculate_concentration_risk(portfolio_assets)
        
        logger.info("Analyzing sector exposure...")
        exposure = analyze_sector_exposure(stock_assets)
        
        portfolio_beta = None
        var_metrics = {}
        volatility = {}
        downside_metrics = {}
        correlation_data = None
        
        if len(asset_returns) > 0:
            logger.info("Calculating portfolio returns...")
            portfolio_returns = calculate_portfolio_returns(asset_returns, stock_assets, total_value)
            
            if len(portfolio_returns) > 30 and len(market_returns) > 30:
                logger.info("Calculating portfolio beta...")
                portfolio_beta = calculate_portfolio_beta(portfolio_returns, market_returns)
            
            if len(portfolio_returns) > 30:
                logger.info("Calculating VaR metrics...")
                var_metrics = {
                    "var_95_historical": calculate_var_historical(portfolio_returns, 0.95),
                    "var_99_historical": calculate_var_historical(portfolio_returns, 0.99),
                    "var_95_parametric": calculate_var_parametric(portfolio_returns, 0.95),
                    "var_99_parametric": calculate_var_parametric(portfolio_returns, 0.99),
                }
                
                logger.info("Calculating volatility metrics...")
                daily_vol = portfolio_returns.std()
                annual_vol = daily_vol * np.sqrt(TRADING_DAYS_PER_YEAR)
                volatility = {
                    "portfolio_annual_volatility_pct": round(float(annual_vol) * 100, 2),
                    "by_category": calculate_volatility_by_category(asset_returns, stock_assets)
                }
                
                logger.info("Calculating downside metrics...")
                downside_metrics = calculate_downside_metrics(portfolio_returns)
            
            if len(asset_returns) >= 2:
                logger.info("Calculating correlation matrix...")
                corr_matrix = calculate_correlation_matrix(asset_returns)
                if corr_matrix is not None:
                    correlation_data = {
                        "matrix": corr_matrix.to_dict(),
                        "high_correlations": _find_high_correlations(corr_matrix)
                    }
        
        result = {
            "success": True,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "portfolio_value_eur": round(total_value, 2),
            "analysis_period_days": 252,
            "assets_analyzed": len(asset_returns),
            "total_assets": len(portfolio_assets),
            "beta": portfolio_beta,
            "var_metrics": var_metrics,
            "concentration": concentration,
            "exposure": exposure,
            "volatility": volatility,
            "downside_metrics": downside_metrics,
            "correlation": correlation_data,
        }
        
        logger.info("Portfolio risk analysis completed successfully")
        return result
        
    except ValueError as e:
        logger.error(f"Risk analysis failed (configuration error): {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "configuration"
        }
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": "unexpected"
        }


def _find_high_correlations(corr_matrix: pd.DataFrame, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find pairs of assets with high correlation.

    Args:
        corr_matrix: Correlation matrix
        threshold: Correlation threshold (default 0.7)

    Returns:
        list: High correlation pairs
    """
    high_corr = []
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            asset1 = corr_matrix.columns[i]
            asset2 = corr_matrix.columns[j]
            corr_value = corr_matrix.iloc[i, j]
            
            if abs(corr_value) >= threshold:
                high_corr.append({
                    "asset1": asset1,
                    "asset2": asset2,
                    "correlation": round(float(corr_value), 3)
                })
    
    high_corr.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    return high_corr
