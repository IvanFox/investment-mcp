"""
Interactive Portfolio Dashboard Generation

Generates HTML dashboards with Plotly charts showing portfolio performance,
allocation, individual asset trends, and risk metrics over time.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from . import storage

logger = logging.getLogger(__name__)

DASHBOARD_DIR = "dashboards"
DASHBOARD_FILE = "portfolio_dashboard.html"

# Time period mappings
PERIOD_MAPPING = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "1y": timedelta(days=365),
    "all": None
}


def _filter_snapshots_by_period(
    snapshots: List[Dict[str, Any]], 
    period: str
) -> List[Dict[str, Any]]:
    """
    Filter snapshots by time period.
    
    Args:
        snapshots: List of all snapshots
        period: One of "7d", "30d", "90d", "1y", "all"
    
    Returns:
        Filtered list of snapshots
    """
    if period not in PERIOD_MAPPING:
        logger.warning(f"Invalid period '{period}', defaulting to 'all'")
        period = "all"
    
    delta = PERIOD_MAPPING[period]
    
    if delta is None:
        return snapshots
    
    if not snapshots:
        return []
    
    # Get cutoff date
    latest_snapshot = snapshots[-1]
    latest_date = datetime.fromisoformat(latest_snapshot["timestamp"].replace("Z", "+00:00"))
    cutoff_date = latest_date - delta
    
    # Filter snapshots
    filtered = []
    for snapshot in snapshots:
        snap_date = datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))
        if snap_date >= cutoff_date:
            filtered.append(snapshot)
    
    return filtered


def _prepare_portfolio_timeseries(
    snapshots: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Convert snapshots to time-series DataFrame for portfolio totals.
    
    Returns:
        DataFrame with columns: timestamp, total_value_eur
    """
    data = []
    for snapshot in snapshots:
        data.append({
            "timestamp": datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00")),
            "total_value_eur": snapshot["total_value_eur"]
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    return df


def _prepare_category_timeseries(
    snapshots: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Convert snapshots to time-series DataFrame for category allocation.
    
    Returns:
        DataFrame with columns: timestamp, category1, category2, ...
    """
    data = []
    for snapshot in snapshots:
        row = {"timestamp": datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))}
        
        # Aggregate by category
        for asset in snapshot.get("assets", []):
            category = asset.get("category", "Other")
            value = asset.get("current_value_eur", 0.0)
            row[category] = row.get(category, 0.0) + value
        
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    df = df.fillna(0)
    return df


def _prepare_asset_timeseries(
    snapshots: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Convert snapshots to time-series DataFrame for individual assets.
    
    Returns:
        DataFrame with columns: timestamp, asset1, asset2, ...
    """
    data = []
    for snapshot in snapshots:
        row = {"timestamp": datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))}
        
        # Add each asset
        for asset in snapshot.get("assets", []):
            name = asset.get("name")
            value = asset.get("current_value_eur", 0.0)
            if name:
                row[name] = value
        
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    df = df.fillna(0)
    return df


def _get_top_assets_by_value(
    latest_snapshot: Dict[str, Any], 
    n: int = 10
) -> List[str]:
    """
    Get top N assets by current value.
    
    Returns:
        List of asset names
    """
    assets = latest_snapshot.get("assets", [])
    
    # Filter out cash and pension for clearer charts
    filtered_assets = [
        asset for asset in assets 
        if asset.get("category") not in ["Cash", "Pension"]
    ]
    
    # Sort by value
    sorted_assets = sorted(
        filtered_assets, 
        key=lambda x: x.get("current_value_eur", 0), 
        reverse=True
    )
    
    return [asset.get("name") for asset in sorted_assets[:n]]


def _prepare_benchmark_data(
    snapshots: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch benchmark data for S&P 500 (SPY) and All-World (VT).
    
    Returns:
        Tuple of (spy_df, vt_df) with columns: timestamp, close
    
    Note: Uses yfinance to fetch benchmark data, normalizes to portfolio start date
    """
    if not snapshots:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get date range
    start_date = datetime.fromisoformat(snapshots[0]["timestamp"].replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(snapshots[-1]["timestamp"].replace("Z", "+00:00"))
    
    # Add buffer
    start_date = start_date - timedelta(days=7)
    end_date = end_date + timedelta(days=1)
    
    try:
        # Fetch SPY data
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(start=start_date, end=end_date)
        spy_df = pd.DataFrame({
            "timestamp": spy_hist.index,
            "close": spy_hist["Close"].values
        })
        # Normalize timezone: convert to UTC if timezone-aware, otherwise make UTC
        if spy_df["timestamp"].dt.tz is not None:
            spy_df["timestamp"] = spy_df["timestamp"].dt.tz_convert("UTC")
        else:
            spy_df["timestamp"] = spy_df["timestamp"].dt.tz_localize("UTC")
        logger.info(f"Fetched {len(spy_df)} SPY benchmark data points")
    except Exception as e:
        logger.error(f"Failed to fetch SPY data: {e}")
        spy_df = pd.DataFrame()
    
    try:
        # Fetch VT data (All-World Index)
        vt = yf.Ticker("VT")
        vt_hist = vt.history(start=start_date, end=end_date)
        vt_df = pd.DataFrame({
            "timestamp": vt_hist.index,
            "close": vt_hist["Close"].values
        })
        # Normalize timezone: convert to UTC if timezone-aware, otherwise make UTC
        if vt_df["timestamp"].dt.tz is not None:
            vt_df["timestamp"] = vt_df["timestamp"].dt.tz_convert("UTC")
        else:
            vt_df["timestamp"] = vt_df["timestamp"].dt.tz_localize("UTC")
        logger.info(f"Fetched {len(vt_df)} VT benchmark data points")
    except Exception as e:
        logger.error(f"Failed to fetch VT data: {e}")
        vt_df = pd.DataFrame()
    
    return spy_df, vt_df


def _create_portfolio_value_chart(
    df: pd.DataFrame,
    spy_df: pd.DataFrame,
    vt_df: pd.DataFrame
) -> go.Figure:
    """
    Create interactive line chart of portfolio value vs benchmarks over time.
    
    Features:
    - Portfolio value (EUR)
    - S&P 500 normalized to same start value
    - All-World Index normalized to same start value
    - Hover tooltips with date, value, and % change
    """
    fig = go.Figure()
    
    if df.empty:
        return fig
    
    # Portfolio line
    initial_value = df.iloc[0]["total_value_eur"]
    df["pct_change"] = ((df["total_value_eur"] - initial_value) / initial_value * 100)
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["total_value_eur"],
        mode="lines+markers",
        name="Portfolio",
        line=dict(color="#1f77b4", width=3),
        marker=dict(size=6),
        hovertemplate="<b>Portfolio</b><br>Date: %{x}<br>Value: €%{y:,.2f}<br>Change: %{customdata:.2f}%<extra></extra>",
        customdata=df["pct_change"]
    ))
    
    # Normalize and add SPY benchmark
    if not spy_df.empty:
        # Merge with portfolio dates for alignment
        merged_spy = pd.merge_asof(
            df[["timestamp"]].sort_values("timestamp"),
            spy_df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )
        
        if not merged_spy["close"].isna().all():
            spy_initial = merged_spy.iloc[0]["close"]
            merged_spy["normalized"] = (merged_spy["close"] / spy_initial) * initial_value
            merged_spy["pct_change"] = ((merged_spy["close"] - spy_initial) / spy_initial * 100)
            
            fig.add_trace(go.Scatter(
                x=merged_spy["timestamp"],
                y=merged_spy["normalized"],
                mode="lines",
                name="S&P 500 (SPY)",
                line=dict(color="#ff7f0e", width=2, dash="dash"),
                hovertemplate="<b>S&P 500</b><br>Date: %{x}<br>Value: €%{y:,.2f}<br>Change: %{customdata:.2f}%<extra></extra>",
                customdata=merged_spy["pct_change"]
            ))
    
    # Normalize and add VT benchmark
    if not vt_df.empty:
        merged_vt = pd.merge_asof(
            df[["timestamp"]].sort_values("timestamp"),
            vt_df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )
        
        if not merged_vt["close"].isna().all():
            vt_initial = merged_vt.iloc[0]["close"]
            merged_vt["normalized"] = (merged_vt["close"] / vt_initial) * initial_value
            merged_vt["pct_change"] = ((merged_vt["close"] - vt_initial) / vt_initial * 100)
            
            fig.add_trace(go.Scatter(
                x=merged_vt["timestamp"],
                y=merged_vt["normalized"],
                mode="lines",
                name="All-World (VT)",
                line=dict(color="#2ca02c", width=2, dash="dot"),
                hovertemplate="<b>All-World Index</b><br>Date: %{x}<br>Value: €%{y:,.2f}<br>Change: %{customdata:.2f}%<extra></extra>",
                customdata=merged_vt["pct_change"]
            ))
    
    fig.update_layout(
        title="Portfolio Value vs Benchmarks Over Time",
        xaxis_title="Date",
        yaxis_title="Value (EUR)",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    return fig


def _create_category_allocation_chart(
    df: pd.DataFrame
) -> go.Figure:
    """
    Create stacked area chart of category allocation over time.
    
    Features:
    - Stacked areas for each category
    - Percentages shown in hover
    - Legend toggleable
    """
    fig = go.Figure()
    
    if df.empty or len(df.columns) <= 1:
        return fig
    
    # Get category columns (exclude timestamp)
    categories = [col for col in df.columns if col != "timestamp"]
    
    # Calculate totals for percentages
    df["total"] = df[categories].sum(axis=1)
    
    # Color scheme for categories
    colors = {
        "US Stocks": "#1f77b4",
        "EU Stocks": "#ff7f0e",
        "Bonds": "#2ca02c",
        "ETFs": "#d62728",
        "Pension": "#9467bd",
        "Cash": "#8c564b",
        "Other": "#e377c2"
    }
    
    for category in categories:
        pct = (df[category] / df["total"] * 100).round(2)
        
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[category],
            mode="lines",
            name=category,
            stackgroup="one",
            fillcolor=colors.get(category, "#cccccc"),
            line=dict(width=0.5),
            hovertemplate=f"<b>{category}</b><br>Date: %{{x}}<br>Value: €%{{y:,.2f}}<br>Percentage: %{{customdata:.1f}}%<extra></extra>",
            customdata=pct
        ))
    
    fig.update_layout(
        title="Category Allocation Over Time",
        xaxis_title="Date",
        yaxis_title="Value (EUR)",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    return fig


def _create_asset_performance_chart(
    df: pd.DataFrame,
    default_assets: List[str]
) -> go.Figure:
    """
    Create multi-line chart for individual asset values.
    
    Features:
    - All assets available
    - Top 10 visible by default
    - Multi-select via legend
    - Hover shows asset name, value, % change
    """
    fig = go.Figure()
    
    if df.empty or len(df.columns) <= 1:
        return fig
    
    # Get asset columns (exclude timestamp)
    assets = [col for col in df.columns if col != "timestamp"]
    
    for asset in assets:
        # Check if asset should be visible by default
        visible = "legendonly" if asset not in default_assets else True
        
        # Calculate % change from first value
        asset_data = df[asset]
        if asset_data.sum() > 0:  # Only show assets with values
            initial_value = asset_data[asset_data > 0].iloc[0] if (asset_data > 0).any() else 1
            pct_change = ((asset_data - initial_value) / initial_value * 100).round(2)
            
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df[asset],
                mode="lines+markers",
                name=asset,
                visible=visible,
                line=dict(width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{asset}</b><br>Date: %{{x}}<br>Value: €%{{y:,.2f}}<br>Change: %{{customdata:.2f}}%<extra></extra>",
                customdata=pct_change
            ))
    
    fig.update_layout(
        title="Individual Asset Performance (Top 10 Shown by Default)",
        xaxis_title="Date",
        yaxis_title="Value (EUR)",
        hovermode="x unified",
        template="plotly_white",
        height=600,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig


def _create_top_holdings_chart(
    snapshots: List[Dict[str, Any]]
) -> go.Figure:
    """
    Create chart showing how top 10 holdings change over time.
    
    Features:
    - Line chart showing value evolution of top assets
    """
    fig = go.Figure()
    
    if not snapshots:
        return fig
    
    # Get latest snapshot to determine top holdings
    latest_snapshot = snapshots[-1]
    top_assets = _get_top_assets_by_value(latest_snapshot, n=10)
    
    # Prepare data for top assets
    df = _prepare_asset_timeseries(snapshots)
    
    for asset in top_assets:
        if asset in df.columns:
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df[asset],
                mode="lines+markers",
                name=asset,
                line=dict(width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{asset}</b><br>Date: %{{x}}<br>Value: €%{{y:,.2f}}<extra></extra>"
            ))
    
    fig.update_layout(
        title="Top 10 Holdings Evolution",
        xaxis_title="Date",
        yaxis_title="Value (EUR)",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    return fig


def _create_gainloss_chart(
    latest_snapshot: Dict[str, Any]
) -> go.Figure:
    """
    Create bar chart of gain/loss by asset.
    
    Features:
    - Horizontal bars sorted by gain/loss
    - Green for gains, red for losses
    - Shows EUR value and percentage
    """
    fig = go.Figure()
    
    assets = latest_snapshot.get("assets", [])
    
    # Calculate gain/loss for each asset
    data = []
    for asset in assets:
        name = asset.get("name")
        current_value = asset.get("current_value_eur", 0.0)
        purchase_price = asset.get("purchase_price_total_eur", 0.0)
        
        if purchase_price > 0 and asset.get("category") not in ["Cash", "Pension"]:
            gain_loss = current_value - purchase_price
            gain_loss_pct = (gain_loss / purchase_price * 100)
            
            data.append({
                "name": name,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct
            })
    
    if not data:
        return fig
    
    # Sort by gain/loss
    data.sort(key=lambda x: x["gain_loss"])
    
    df = pd.DataFrame(data)
    
    # Color based on positive/negative
    colors = ["#2ca02c" if x >= 0 else "#d62728" for x in df["gain_loss"]]
    
    fig.add_trace(go.Bar(
        y=df["name"],
        x=df["gain_loss"],
        orientation="h",
        marker=dict(color=colors),
        hovertemplate="<b>%{y}</b><br>Gain/Loss: €%{x:,.2f}<br>Percentage: %{customdata:.2f}%<extra></extra>",
        customdata=df["gain_loss_pct"]
    ))
    
    fig.update_layout(
        title="Current Gain/Loss by Asset",
        xaxis_title="Gain/Loss (EUR)",
        yaxis_title="",
        template="plotly_white",
        height=max(400, len(data) * 25),
        showlegend=False
    )
    
    return fig


def _create_quantity_changes_chart(
    snapshots: List[Dict[str, Any]]
) -> go.Figure:
    """
    Create scatter/line chart showing buy/sell activity over time.
    
    Features:
    - Markers for each transaction
    - Size represents transaction size
    - Color: green = buy, red = sell
    """
    fig = go.Figure()
    
    if len(snapshots) < 2:
        return fig
    
    # Track quantity changes
    transactions = []
    
    for i in range(1, len(snapshots)):
        prev_snapshot = snapshots[i - 1]
        curr_snapshot = snapshots[i]
        
        timestamp = datetime.fromisoformat(curr_snapshot["timestamp"].replace("Z", "+00:00"))
        
        # Build asset maps
        prev_assets = {asset["name"]: asset for asset in prev_snapshot.get("assets", [])}
        curr_assets = {asset["name"]: asset for asset in curr_snapshot.get("assets", [])}
        
        # Check for quantity changes
        for name in set(list(prev_assets.keys()) + list(curr_assets.keys())):
            prev_qty = prev_assets.get(name, {}).get("quantity", 0.0)
            curr_qty = curr_assets.get(name, {}).get("quantity", 0.0)
            
            qty_change = curr_qty - prev_qty
            
            if abs(qty_change) > 0.01:  # Threshold to avoid noise
                curr_value = curr_assets.get(name, {}).get("current_value_eur", 0.0)
                
                transactions.append({
                    "timestamp": timestamp,
                    "name": name,
                    "qty_change": qty_change,
                    "value": curr_value,
                    "type": "Buy" if qty_change > 0 else "Sell"
                })
    
    if not transactions:
        # Add a note that no transactions detected
        fig.add_annotation(
            text="No buy/sell transactions detected in snapshot history",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Transaction Timeline",
            template="plotly_white",
            height=400
        )
        return fig
    
    df = pd.DataFrame(transactions)
    
    # Separate buys and sells
    buys = df[df["type"] == "Buy"]
    sells = df[df["type"] == "Sell"]
    
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys["timestamp"],
            y=buys["value"],
            mode="markers",
            name="Buy",
            marker=dict(
                color="#2ca02c",
                size=buys["qty_change"].abs() * 2 + 5,
                symbol="triangle-up"
            ),
            hovertemplate="<b>BUY: %{customdata}</b><br>Date: %{x}<br>Value: €%{y:,.2f}<extra></extra>",
            customdata=buys["name"]
        ))
    
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells["timestamp"],
            y=sells["value"],
            mode="markers",
            name="Sell",
            marker=dict(
                color="#d62728",
                size=sells["qty_change"].abs() * 2 + 5,
                symbol="triangle-down"
            ),
            hovertemplate="<b>SELL: %{customdata}</b><br>Date: %{x}<br>Value: €%{y:,.2f}<extra></extra>",
            customdata=sells["name"]
        ))
    
    fig.update_layout(
        title="Transaction Timeline (Buy/Sell Activity)",
        xaxis_title="Date",
        yaxis_title="Position Value (EUR)",
        template="plotly_white",
        height=400
    )
    
    return fig


def _create_currency_exposure_chart(
    snapshots: List[Dict[str, Any]]
) -> go.Figure:
    """
    Create stacked area chart of currency exposure.
    
    Features:
    - USD, EUR, GBP exposure over time
    - Based on asset geography/category
    """
    fig = go.Figure()
    
    if not snapshots:
        return fig
    
    # Map categories to currencies (simplified assumption)
    currency_map = {
        "US Stocks": "USD",
        "EU Stocks": "EUR",
        "Bonds": "EUR",
        "ETFs": "Mixed",
        "Pension": "EUR",
        "Cash": "EUR"
    }
    
    data = []
    for snapshot in snapshots:
        row = {"timestamp": datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00"))}
        
        # Aggregate by currency
        for asset in snapshot.get("assets", []):
            category = asset.get("category", "Other")
            currency = currency_map.get(category, "Other")
            value = asset.get("current_value_eur", 0.0)
            row[currency] = row.get(currency, 0.0) + value
        
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    df = df.fillna(0)
    
    currencies = [col for col in df.columns if col != "timestamp"]
    
    color_map = {
        "USD": "#1f77b4",
        "EUR": "#2ca02c",
        "GBP": "#ff7f0e",
        "Mixed": "#9467bd",
        "Other": "#8c564b"
    }
    
    for currency in currencies:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[currency],
            mode="lines",
            name=currency,
            stackgroup="one",
            fillcolor=color_map.get(currency, "#cccccc"),
            line=dict(width=0.5),
            hovertemplate=f"<b>{currency}</b><br>Date: %{{x}}<br>Value: €%{{y:,.2f}}<extra></extra>"
        ))
    
    fig.update_layout(
        title="Currency Exposure Over Time",
        xaxis_title="Date",
        yaxis_title="Value (EUR)",
        hovermode="x unified",
        template="plotly_white",
        height=400
    )
    
    return fig


def _create_metrics_dashboard(
    snapshots: List[Dict[str, Any]]
) -> go.Figure:
    """
    Create subplot dashboard with key metrics:
    - Sharpe Ratio over time (approximated)
    - Maximum Drawdown visualization
    - Cumulative Returns
    - Contribution Analysis (recent period)
    
    Features:
    - 2x2 subplot grid
    - Each metric toggleable
    """
    if len(snapshots) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Need more snapshot history to calculate metrics",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Risk Metrics Dashboard",
            template="plotly_white",
            height=800
        )
        return fig
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Cumulative Returns (%)",
            "Maximum Drawdown",
            "Rolling Volatility (30-day)",
            "Value Change Distribution"
        )
    )
    
    # Prepare portfolio time series
    df = _prepare_portfolio_timeseries(snapshots)
    
    # 1. Cumulative Returns
    initial_value = df.iloc[0]["total_value_eur"]
    df["cum_return"] = ((df["total_value_eur"] - initial_value) / initial_value * 100)
    
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["cum_return"],
            mode="lines+markers",
            name="Cumulative Return",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="Date: %{x}<br>Return: %{y:.2f}%<extra></extra>"
        ),
        row=1, col=1
    )
    
    # 2. Maximum Drawdown
    df["peak"] = df["total_value_eur"].cummax()
    df["drawdown"] = ((df["total_value_eur"] - df["peak"]) / df["peak"] * 100)
    
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["drawdown"],
            mode="lines",
            name="Drawdown",
            fill="tozeroy",
            line=dict(color="#d62728", width=2),
            hovertemplate="Date: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>"
        ),
        row=1, col=2
    )
    
    # 3. Rolling Volatility (30-day window)
    if len(df) > 30:
        df["daily_return"] = df["total_value_eur"].pct_change()
        df["rolling_vol"] = df["daily_return"].rolling(window=min(30, len(df))).std() * np.sqrt(252) * 100
        
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["rolling_vol"],
                mode="lines",
                name="Volatility",
                line=dict(color="#ff7f0e", width=2),
                hovertemplate="Date: %{x}<br>Volatility: %{y:.2f}%<extra></extra>"
            ),
            row=2, col=1
        )
    
    # 4. Value Change Distribution
    df["value_change"] = df["total_value_eur"].diff()
    
    fig.add_trace(
        go.Histogram(
            x=df["value_change"].dropna(),
            name="Value Changes",
            marker=dict(color="#2ca02c"),
            nbinsx=20,
            hovertemplate="Change: €%{x:,.2f}<br>Count: %{y}<extra></extra>"
        ),
        row=2, col=2
    )
    
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Date", row=1, col=2)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_xaxes(title_text="Value Change (EUR)", row=2, col=2)
    
    fig.update_yaxes(title_text="Return (%)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=1, col=2)
    fig.update_yaxes(title_text="Volatility (%)", row=2, col=1)
    fig.update_yaxes(title_text="Frequency", row=2, col=2)
    
    fig.update_layout(
        title_text="Risk Metrics Dashboard",
        template="plotly_white",
        height=800,
        showlegend=False
    )
    
    return fig


def _create_dashboard_css() -> str:
    """
    Generate CSS styles for dashboard.
    
    Returns:
        CSS string with responsive layout rules
    """
    return """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            margin: 0 0 10px 0;
            color: #1f77b4;
        }
        .header .subtitle {
            color: #666;
            font-size: 14px;
        }
        .controls {
            position: sticky;
            top: 20px;
            background-color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 1000;
        }
        .controls label {
            font-weight: 600;
            margin-right: 10px;
        }
        .controls select {
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            background-color: white;
            cursor: pointer;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #1f77b4;
        }
        .stat-card h3 {
            margin: 0 0 5px 0;
            font-size: 14px;
            color: #666;
        }
        .stat-card p {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }
        .chart-section {
            margin-bottom: 40px;
        }
        .chart-section h2 {
            margin-bottom: 15px;
            color: #333;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 15px;
            }
            .stats {
                grid-template-columns: 1fr;
            }
            .controls {
                position: relative;
                top: 0;
            }
        }
    </style>
    """


def _create_time_selector_js() -> str:
    """
    Generate JavaScript for time period selector.
    
    Returns:
        JavaScript code that filters data and redraws charts
    """
    return """
    <script>
        // Note: Time filtering is handled server-side
        // This function triggers a reload with new time period
        function updateDashboard(period) {
            // Store selected period
            localStorage.setItem('dashboard_period', period);
            
            // In a full implementation, this would:
            // 1. Call Python backend to regenerate with new period
            // 2. Or filter data client-side using Plotly.react()
            
            // For now, show a message that regeneration is needed
            console.log('Time period selected:', period);
            alert('To view this time period, please regenerate the dashboard with: generate_portfolio_dashboard("' + period + '")');
        }
        
        // Restore saved period on load
        window.addEventListener('DOMContentLoaded', function() {
            const saved = localStorage.getItem('dashboard_period');
            if (saved) {
                document.getElementById('time-period').value = saved;
            }
        });
    </script>
    """


def _generate_dashboard_html(
    figures: Dict[str, go.Figure],
    snapshots: List[Dict[str, Any]],
    period: str
) -> str:
    """
    Generate complete HTML dashboard with all charts and interactivity.
    
    Args:
        figures: Dict of chart_name -> plotly figure
        snapshots: All snapshots for metadata
        period: Current time period selection
    
    Returns:
        Complete HTML string
    """
    # Calculate summary statistics
    if not snapshots:
        return "<html><body><h1>No data available</h1></body></html>"
    
    latest = snapshots[-1]
    first = snapshots[0]
    
    current_value = latest["total_value_eur"]
    initial_value = first["total_value_eur"]
    total_change = current_value - initial_value
    total_change_pct = (total_change / initial_value * 100) if initial_value > 0 else 0
    
    start_date = datetime.fromisoformat(first["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
    end_date = datetime.fromisoformat(latest["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
    
    # Generate HTML
    html_parts = []
    
    # HTML header
    html_parts.append("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Portfolio Dashboard - Investment MCP Agent</title>
        <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    """)
    
    html_parts.append(_create_dashboard_css())
    html_parts.append("</head><body>")
    
    # Container
    html_parts.append('<div class="container">')
    
    # Header
    html_parts.append(f"""
    <div class="header">
        <h1>📊 Portfolio Dashboard</h1>
        <div class="subtitle">
            Investment MCP Agent | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
    """)
    
    # Controls
    html_parts.append(f"""
    <div class="controls">
        <label for="time-period">Time Period:</label>
        <select id="time-period" onchange="updateDashboard(this.value)">
            <option value="7d" {"selected" if period == "7d" else ""}>Last 7 Days</option>
            <option value="30d" {"selected" if period == "30d" else ""}>Last 30 Days</option>
            <option value="90d" {"selected" if period == "90d" else ""}>Last 90 Days</option>
            <option value="1y" {"selected" if period == "1y" else ""}>Last Year</option>
            <option value="all" {"selected" if period == "all" else ""}>All Time</option>
        </select>
    </div>
    """)
    
    # Summary statistics
    change_color = "#2ca02c" if total_change >= 0 else "#d62728"
    change_sign = "+" if total_change >= 0 else ""
    
    html_parts.append(f"""
    <div class="stats">
        <div class="stat-card">
            <h3>Current Value</h3>
            <p>€{current_value:,.2f}</p>
        </div>
        <div class="stat-card">
            <h3>Total Change</h3>
            <p style="color: {change_color}">{change_sign}€{total_change:,.2f}</p>
        </div>
        <div class="stat-card">
            <h3>Return</h3>
            <p style="color: {change_color}">{change_sign}{total_change_pct:.2f}%</p>
        </div>
        <div class="stat-card">
            <h3>Snapshots</h3>
            <p>{len(snapshots)}</p>
        </div>
        <div class="stat-card">
            <h3>Date Range</h3>
            <p style="font-size: 14px">{start_date} to {end_date}</p>
        </div>
    </div>
    """)
    
    # Charts
    chart_order = [
        ("portfolio_value", "Portfolio Value vs Benchmarks"),
        ("category_allocation", "Category Allocation"),
        ("asset_performance", "Individual Asset Performance"),
        ("top_holdings", "Top Holdings Evolution"),
        ("gainloss", "Gain/Loss Analysis"),
        ("transactions", "Transaction Timeline"),
        ("currency", "Currency Exposure"),
        ("metrics", "Risk Metrics")
    ]
    
    for chart_id, chart_title in chart_order:
        if chart_id in figures:
            html_parts.append(f'<div class="chart-section" id="{chart_id}-section">')
            html_parts.append(f'<div id="{chart_id}"></div>')
            html_parts.append('</div>')
    
    # Footer
    html_parts.append("""
    <div class="footer">
        Generated by Investment MCP Agent | Data stored securely
    </div>
    """)
    
    html_parts.append('</div>')  # Close container
    
    # Add Plotly chart scripts
    html_parts.append('<script>')
    for chart_id, chart_title in chart_order:
        if chart_id in figures:
            fig_json = figures[chart_id].to_json()
            html_parts.append(f"Plotly.newPlot('{chart_id}', {fig_json});")
    html_parts.append('</script>')
    
    # Add time selector JS
    html_parts.append(_create_time_selector_js())
    
    html_parts.append('</body></html>')
    
    return '\n'.join(html_parts)


def generate_portfolio_dashboard(
    time_period: str = "all",
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate interactive HTML dashboard with portfolio visualizations.
    
    Args:
        time_period: One of "7d", "30d", "90d", "1y", "all" (default: "all")
        force_regenerate: If True, regenerate even if recent dashboard exists
    
    Returns:
        dict: {
            "success": bool,
            "file_path": str (absolute path),
            "file_url": str (file:// URL),
            "snapshot_count": int,
            "date_range": {"start": str, "end": str},
            "generated_at": str,
            "error": str (if success=False)
        }
    
    Raises:
        ValueError: If insufficient snapshots (need at least 2)
        IOError: If dashboard directory cannot be created
    """
    try:
        logger.info(f"Generating portfolio dashboard for period: {time_period}")
        
        # Get all snapshots
        all_snapshots = storage.get_all_snapshots()
        
        if len(all_snapshots) < 2:
            return {
                "success": False,
                "error": f"Need at least 2 snapshots to generate dashboard (found {len(all_snapshots)})"
            }
        
        # Filter by time period
        snapshots = _filter_snapshots_by_period(all_snapshots, time_period)
        
        if len(snapshots) < 2:
            return {
                "success": False,
                "error": f"Need at least 2 snapshots in selected period (found {len(snapshots)})"
            }
        
        logger.info(f"Processing {len(snapshots)} snapshots")
        
        # Prepare data
        portfolio_df = _prepare_portfolio_timeseries(snapshots)
        category_df = _prepare_category_timeseries(snapshots)
        asset_df = _prepare_asset_timeseries(snapshots)
        
        # Get benchmark data
        spy_df, vt_df = _prepare_benchmark_data(snapshots)
        
        # Get top assets
        top_assets = _get_top_assets_by_value(snapshots[-1], n=10)
        
        # Generate all charts
        figures = {}
        
        logger.info("Creating portfolio value chart...")
        figures["portfolio_value"] = _create_portfolio_value_chart(portfolio_df, spy_df, vt_df)
        
        logger.info("Creating category allocation chart...")
        figures["category_allocation"] = _create_category_allocation_chart(category_df)
        
        logger.info("Creating asset performance chart...")
        figures["asset_performance"] = _create_asset_performance_chart(asset_df, top_assets)
        
        logger.info("Creating top holdings chart...")
        figures["top_holdings"] = _create_top_holdings_chart(snapshots)
        
        logger.info("Creating gain/loss chart...")
        figures["gainloss"] = _create_gainloss_chart(snapshots[-1])
        
        logger.info("Creating transaction timeline...")
        figures["transactions"] = _create_quantity_changes_chart(snapshots)
        
        logger.info("Creating currency exposure chart...")
        figures["currency"] = _create_currency_exposure_chart(snapshots)
        
        logger.info("Creating metrics dashboard...")
        figures["metrics"] = _create_metrics_dashboard(snapshots)
        
        # Generate HTML
        logger.info("Generating HTML dashboard...")
        html_content = _generate_dashboard_html(figures, snapshots, time_period)
        
        # Ensure dashboard directory exists
        dashboard_path = Path(DASHBOARD_DIR)
        dashboard_path.mkdir(exist_ok=True)
        
        # Write HTML file
        output_file = dashboard_path / DASHBOARD_FILE
        output_file.write_text(html_content, encoding="utf-8")
        
        abs_path = output_file.absolute()
        file_url = f"file://{abs_path}"
        
        # Get date range
        start_date = datetime.fromisoformat(snapshots[0]["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        end_date = datetime.fromisoformat(snapshots[-1]["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        
        logger.info(f"Dashboard generated successfully: {abs_path}")
        
        return {
            "success": True,
            "file_path": str(abs_path),
            "file_url": file_url,
            "snapshot_count": len(snapshots),
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        error_msg = f"Failed to generate dashboard: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg
        }
