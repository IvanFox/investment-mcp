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
            # Skip cash and pension positions (only show securities)
            if "Cash" in name or "Pension" in name:
                continue

            # Also check category
            asset_info = curr_assets.get(name) or prev_assets.get(name)
            if asset_info:
                category = asset_info.get("category", "")
                if category in ["Cash", "Pension"]:
                    continue

            prev_qty = prev_assets.get(name, {}).get("quantity", 0.0)
            curr_qty = curr_assets.get(name, {}).get("quantity", 0.0)

            qty_change = curr_qty - prev_qty

            if abs(qty_change) > 0.01:  # Threshold to avoid noise
                # For buys, show current value (position after buy)
                # For sells, show previous value (what was sold)
                if qty_change > 0:  # Buy
                    value = curr_assets.get(name, {}).get("current_value_eur", 0.0)
                else:  # Sell
                    value = prev_assets.get(name, {}).get("current_value_eur", 0.0)

                transactions.append({
                    "timestamp": timestamp,
                    "name": name,
                    "qty_change": qty_change,
                    "value": value,
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
            x=buys["timestamp"].tolist(),
            y=buys["value"].tolist(),
            mode="markers",
            name="Buy",
            marker=dict(
                color="#10B981",
                size=12,
                symbol="triangle-up",
                line=dict(color="white", width=1)
            ),
            hovertemplate="<b>BUY: %{customdata}</b><br>Date: %{x}<br>Value: €%{y:,.2f}<extra></extra>",
            customdata=buys["name"].tolist()
        ))
    
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells["timestamp"].tolist(),
            y=sells["value"].tolist(),
            mode="markers",
            name="Sell",
            marker=dict(
                color="#EF4444",
                size=12,
                symbol="triangle-down",
                line=dict(color="white", width=1)
            ),
            hovertemplate="<b>SELL: %{customdata}</b><br>Date: %{x}<br>Value: €%{y:,.2f}<extra></extra>",
            customdata=sells["name"].tolist()
        ))
    
    fig.update_layout(
        title="Transaction Timeline (Buy/Sell Activity)",
        xaxis_title="Date",
        yaxis_title="Position Value (EUR)",
        template="plotly_white",
        height=500,
        showlegend=True,
        hovermode='closest',
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='#E5E7EB',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#E5E7EB',
            zeroline=False,
            rangemode='tozero'
        )
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


def _create_correlation_heatmap(correlation_matrix: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Create correlation heatmap for top holdings.

    Args:
        correlation_matrix: Full correlation matrix from risk_analysis.py
        top_n: Number of top holdings to include (default 10)

    Returns:
        Plotly heatmap figure
    """
    fig = go.Figure()

    if correlation_matrix.empty or len(correlation_matrix) < 2:
        return fig

    # Limit to top N holdings if needed
    if len(correlation_matrix) > top_n:
        # Take first top_n rows and columns
        corr_subset = correlation_matrix.iloc[:top_n, :top_n]
    else:
        corr_subset = correlation_matrix

    # Create heatmap
    fig.add_trace(go.Heatmap(
        z=corr_subset.values,
        x=corr_subset.columns,
        y=corr_subset.index,
        colorscale="RdBu",
        zmid=0,
        zmin=-1,
        zmax=1,
        text=corr_subset.values,
        texttemplate="%{text:.2f}",
        textfont={"size": 10},
        hovertemplate="<b>%{x} vs %{y}</b><br>Correlation: %{z:.3f}<extra></extra>",
        colorbar=dict(title="Correlation")
    ))

    fig.update_layout(
        title=f"Asset Correlation Matrix (Top {len(corr_subset)} Holdings)",
        xaxis=dict(side="bottom", tickangle=-45),
        yaxis=dict(autorange="reversed"),
        template="plotly_white",
        height=600,
        width=700
    )

    return fig


def _create_realized_gains_chart(sell_transactions: List[Dict[str, Any]]) -> go.Figure:
    """
    Create realized gains tracking charts.

    Args:
        sell_transactions: List of sell transactions from storage

    Returns:
        Plotly figure with subplots:
        - Top: Cumulative realized gains over time
        - Bottom: Monthly/quarterly realized P&L bars
    """
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        subplot_titles=("Cumulative Realized Gains", "Monthly Realized P&L"),
        vertical_spacing=0.12
    )

    if not sell_transactions:
        fig.add_annotation(
            text="No sell transactions available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(height=500, template="plotly_white")
        return fig

    # Sort transactions by date
    sorted_txns = sorted(sell_transactions, key=lambda x: x["date"])

    # Calculate cumulative gains
    cumulative_gains = []
    cumulative_sum = 0
    dates = []

    for txn in sorted_txns:
        # Use the pre-calculated realized gain/loss
        realized_gain = txn.get("realized_gain_loss_eur", 0)
        cumulative_sum += realized_gain
        cumulative_gains.append(cumulative_sum)
        dates.append(datetime.fromisoformat(txn["date"].replace("Z", "+00:00")))

    # Add cumulative gains line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative_gains,
            mode="lines+markers",
            name="Cumulative Gains",
            line=dict(color="#10B981" if cumulative_sum >= 0 else "#EF4444", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor=f"rgba({'16, 185, 129' if cumulative_sum >= 0 else '239, 68, 68'}, 0.1)",
            hovertemplate="Date: %{x}<br>Cumulative: €%{y:,.2f}<extra></extra>"
        ),
        row=1, col=1
    )

    # Aggregate by month for bar chart
    monthly_gains = {}
    for txn in sorted_txns:
        date = datetime.fromisoformat(txn["date"].replace("Z", "+00:00"))
        month_key = date.strftime("%Y-%m")
        # Use the pre-calculated realized gain/loss
        realized_gain = txn.get("realized_gain_loss_eur", 0)
        monthly_gains[month_key] = monthly_gains.get(month_key, 0) + realized_gain

    # Add monthly bars
    months = sorted(monthly_gains.keys())
    gains = [monthly_gains[m] for m in months]
    colors = ["#10B981" if g >= 0 else "#EF4444" for g in gains]

    fig.add_trace(
        go.Bar(
            x=months,
            y=gains,
            name="Monthly P&L",
            marker=dict(color=colors),
            hovertemplate="Month: %{x}<br>P&L: €%{y:,.2f}<extra></extra>"
        ),
        row=2, col=1
    )

    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Cumulative Gain (EUR)", row=1, col=1)
    fig.update_yaxes(title_text="Monthly P&L (EUR)", row=2, col=1)

    fig.update_layout(
        template="plotly_white",
        height=600,
        showlegend=False
    )

    return fig


def _create_cost_basis_waterfall(assets: List[Dict[str, Any]]) -> go.Figure:
    """
    Create waterfall chart showing entry prices vs current value.

    Args:
        assets: List of asset dicts from latest snapshot

    Returns:
        Plotly waterfall figure
    """
    fig = go.Figure()

    if not assets:
        return fig

    # Filter out cash and pension, focus on traded securities
    tradeable = [a for a in assets if a.get("category") not in ["Cash", "Pension"] and a.get("quantity", 0) > 0]

    # Sort by unrealized gain/loss
    for asset in tradeable:
        cost_basis = asset.get("purchase_price_total_eur", 0)
        current_value = asset.get("current_value_eur", 0)
        asset["unrealized_gain"] = current_value - cost_basis

    tradeable.sort(key=lambda x: x["unrealized_gain"], reverse=True)

    # Limit to top 15 for readability
    top_assets = tradeable[:15]

    # Build waterfall data
    names = [a["name"] for a in top_assets]
    cost_basis = [a.get("purchase_price_total_eur", 0) for a in top_assets]
    current_values = [a.get("current_value_eur", 0) for a in top_assets]
    gains = [a["unrealized_gain"] for a in top_assets]

    # Create grouped bar chart (cost basis vs current value)
    fig.add_trace(go.Bar(
        name="Cost Basis",
        x=names,
        y=cost_basis,
        marker=dict(color="#94A3B8"),
        hovertemplate="<b>%{x}</b><br>Cost Basis: €%{y:,.2f}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        name="Current Value",
        x=names,
        y=current_values,
        marker=dict(
            color=["#10B981" if g >= 0 else "#EF4444" for g in gains]
        ),
        hovertemplate="<b>%{x}</b><br>Current: €%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="Cost Basis vs Current Value (Top 15 Positions)",
        xaxis_title="Asset",
        yaxis_title="Value (EUR)",
        xaxis=dict(tickangle=-45),
        barmode="group",
        template="plotly_white",
        height=500,
        hovermode="x unified"
    )

    return fig


def _create_attribution_chart(movers: List[Dict[str, Any]]) -> go.Figure:
    """
    Create bar chart showing which assets contributed to portfolio change.

    Args:
        movers: List of {name, change_eur, contribution_pct, is_gainer}

    Returns:
        Plotly bar figure
    """
    fig = go.Figure()

    if not movers:
        return fig

    # Take top 10 by absolute contribution
    top_movers = sorted(movers, key=lambda x: abs(x.get("contribution_pct", 0)), reverse=True)[:10]

    names = [m["name"] for m in top_movers]
    contributions = [m["contribution_pct"] for m in top_movers]
    colors = ["#10B981" if m.get("is_gainer", False) else "#EF4444" for m in top_movers]

    fig.add_trace(go.Bar(
        x=contributions,
        y=names,
        orientation="h",
        marker=dict(color=colors),
        hovertemplate="<b>%{y}</b><br>Contribution: %{x:.1f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Top 10 Contributors to Portfolio Change",
        xaxis_title="Contribution to Total Change (%)",
        yaxis_title="Asset",
        template="plotly_white",
        height=500
    )

    return fig


def _create_hhi_trend_chart(snapshots: List[Dict[str, Any]]) -> go.Figure:
    """
    Create line chart showing HHI concentration index over time.

    Args:
        snapshots: List of portfolio snapshots

    Returns:
        Plotly line figure
    """
    fig = go.Figure()

    if len(snapshots) < 2:
        return fig

    # Calculate HHI for each snapshot
    dates = []
    hhi_values = []

    for snapshot in snapshots:
        total_value = snapshot.get("total_value_eur", 0)
        if total_value == 0:
            continue

        # Calculate HHI (sum of squared weight percentages)
        hhi = 0
        for asset in snapshot.get("assets", []):
            weight = asset.get("current_value_eur", 0) / total_value
            hhi += weight ** 2

        dates.append(datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00")))
        hhi_values.append(hhi * 10000)  # Scale to 0-10000

    fig.add_trace(go.Scatter(
        x=dates,
        y=hhi_values,
        mode="lines+markers",
        name="HHI",
        line=dict(color="#8B5CF6", width=2),
        marker=dict(size=6),
        hovertemplate="Date: %{x}<br>HHI: %{y:.0f}<extra></extra>"
    ))

    # Add reference lines
    fig.add_hline(y=1500, line_dash="dash", line_color="gray",
                  annotation_text="Unconcentrated (< 1500)")
    fig.add_hline(y=2500, line_dash="dash", line_color="orange",
                  annotation_text="Moderately Concentrated (> 2500)")

    fig.update_layout(
        title="Portfolio Concentration Over Time (HHI Index)",
        xaxis_title="Date",
        yaxis_title="HHI (0-10000)",
        template="plotly_white",
        height=400
    )

    return fig


def _create_volatility_by_category_chart(risk_data: Dict[str, Any]) -> go.Figure:
    """
    Create bar chart comparing volatility across categories.

    Args:
        risk_data: Risk analysis results from risk_analysis.py

    Returns:
        Plotly bar figure
    """
    fig = go.Figure()

    volatility_by_cat = risk_data.get("volatility", {}).get("by_category", {})

    if not volatility_by_cat:
        return fig

    categories = list(volatility_by_cat.keys())
    volatilities = list(volatility_by_cat.values())

    # Color code by volatility level
    colors = []
    for vol in volatilities:
        if vol < 15:
            colors.append("#10B981")  # Low volatility - green
        elif vol < 25:
            colors.append("#F59E0B")  # Medium volatility - amber
        else:
            colors.append("#EF4444")  # High volatility - red

    fig.add_trace(go.Bar(
        x=categories,
        y=volatilities,
        marker=dict(color=colors),
        hovertemplate="<b>%{x}</b><br>Volatility: %{y:.1f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Annualized Volatility by Category",
        xaxis_title="Category",
        yaxis_title="Volatility (%)",
        xaxis=dict(tickangle=-45),
        template="plotly_white",
        height=400
    )

    return fig


def _create_dashboard_css() -> str:
    """
    Generate modern CSS styles for dashboard with design system.

    Returns:
        CSS string with responsive layout rules and component styles
    """
    return """
    <style>
        :root {
            /* Color Palette */
            --portfolio-primary: #3B82F6;
            --portfolio-gain: #10B981;
            --portfolio-loss: #EF4444;
            --benchmark-spy: #F59E0B;
            --benchmark-vt: #8B5CF6;

            /* Neutrals */
            --bg-primary: #FFFFFF;
            --bg-secondary: #F9FAFB;
            --bg-card: #FFFFFF;
            --border: #E5E7EB;
            --text-primary: #111827;
            --text-secondary: #6B7280;

            /* Categories */
            --cat-us-stocks: #3B82F6;
            --cat-eu-stocks: #F59E0B;
            --cat-bonds: #10B981;
            --cat-etfs: #EF4444;
            --cat-pension: #8B5CF6;
            --cat-cash: #6B7280;
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* View Headers */
        .view-header {
            margin-bottom: 32px;
        }

        .view-title {
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0 0 8px 0;
            color: var(--text-primary);
        }

        .view-subtitle {
            font-size: 16px;
            color: var(--text-secondary);
            margin: 0;
        }

        .view-updated {
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* Grid System */
        .grid {
            display: grid;
            gap: 20px;
            margin-bottom: 32px;
        }

        /* KPI Cards */
        .kpi-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
            border: 1px solid var(--border);
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .kpi-label {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .kpi-value {
            font-size: 36px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            margin-bottom: 8px;
        }

        .kpi-card.positive .kpi-value {
            color: var(--portfolio-gain);
        }

        .kpi-card.negative .kpi-value {
            color: var(--portfolio-loss);
        }

        .kpi-change {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            font-weight: 600;
        }

        .kpi-change.positive {
            color: var(--portfolio-gain);
        }

        .kpi-change.negative {
            color: var(--portfolio-loss);
        }

        .kpi-subtitle {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 8px;
        }

        /* Sections */
        .section {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin: 0;
            color: var(--text-primary);
        }

        /* Attribution Table */
        .attribution-table-container {
            overflow-x: auto;
        }

        .attribution-table {
            width: 100%;
            border-collapse: collapse;
        }

        .attribution-table thead th {
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .attribution-table tbody tr {
            border-bottom: 1px solid var(--border);
        }

        .attribution-table tbody tr:hover {
            background-color: var(--bg-secondary);
        }

        .attribution-table td {
            padding: 16px 12px;
        }

        .attr-icon {
            font-size: 16px;
            width: 24px;
        }

        .attribution-row.gainer .attr-icon {
            color: var(--portfolio-gain);
        }

        .attribution-row.loser .attr-icon {
            color: var(--portfolio-loss);
        }

        .attr-name {
            font-weight: 600;
            font-size: 15px;
        }

        .attr-change {
            font-family: 'SF Mono', 'Roboto Mono', monospace;
            font-variant-numeric: tabular-nums;
        }

        .change-eur {
            font-size: 16px;
            font-weight: 600;
        }

        .change-pct {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .attr-change.positive .change-eur {
            color: var(--portfolio-gain);
        }

        .attr-change.negative .change-eur {
            color: var(--portfolio-loss);
        }

        .contribution-bar-container {
            position: relative;
            height: 24px;
            width: 100%;
            max-width: 200px;
        }

        .contribution-bar {
            position: absolute;
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .contribution-bar.gainer {
            background: var(--portfolio-gain);
        }

        .contribution-bar.loser {
            background: var(--portfolio-loss);
        }

        .contribution-text {
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 12px;
            font-weight: 600;
            color: white;
        }

        /* Chart Sections */
        .chart-section {
            margin-bottom: 40px;
        }

        .chart-section h2 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--text-primary);
        }

        /* View Switcher */
        .view-switcher {
            display: flex;
            gap: 8px;
            padding: 16px;
            background: var(--bg-card);
            border-radius: 12px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }

        .view-btn {
            padding: 10px 20px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 14px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .view-btn:hover {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .view-btn.active {
            background: var(--portfolio-primary);
            color: white;
        }

        /* Controls */
        .controls {
            position: sticky;
            top: 20px;
            background-color: var(--bg-card);
            padding: 16px;
            margin-bottom: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 1000;
            border: 1px solid var(--border);
        }

        .controls label {
            font-weight: 600;
            margin-right: 12px;
            color: var(--text-primary);
        }

        .controls select {
            padding: 10px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            background-color: var(--bg-card);
            color: var(--text-primary);
            cursor: pointer;
            font-weight: 500;
        }

        .controls select:focus {
            outline: none;
            border-color: var(--portfolio-primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* Stats (legacy) */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }

        .stat-card {
            background-color: var(--bg-card);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .stat-card h3 {
            margin: 0 0 8px 0;
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stat-card p {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
            font-variant-numeric: tabular-nums;
        }

        /* Sparkline */
        .sparkline-container {
            width: 100%;
            height: 60px;
        }

        /* Footer */
        .footer {
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--text-secondary);
            font-size: 14px;
        }

        /* Info Messages */
        .info-message {
            background: #EFF6FF;
            border-left: 4px solid var(--portfolio-primary);
            padding: 16px;
            border-radius: 8px;
            margin: 24px 0;
        }

        .info-message p {
            margin: 8px 0;
            color: #1E40AF;
        }

        /* Mobile Responsiveness */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }

            .view-title {
                font-size: 24px;
            }

            .grid {
                grid-template-columns: 1fr !important;
            }

            .kpi-value {
                font-size: 28px;
            }

            .controls {
                position: relative;
                top: 0;
            }

            .view-switcher {
                flex-wrap: wrap;
            }

            .attribution-table {
                font-size: 14px;
            }

            .attr-name {
                font-size: 14px;
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


def _wrap_view_html(
    view_content: str,
    title: str,
    snapshots: List[Dict[str, Any]],
    period: str
) -> str:
    """
    Wrap view content in complete HTML page with headers, CSS, and scripts.

    Args:
        view_content: HTML content from view (e.g., DailyOverviewView)
        title: Page title
        snapshots: All snapshots for metadata
        period: Current time period selection

    Returns:
        Complete HTML string
    """
    html_parts = []

    # HTML header
    html_parts.append(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Investment MCP Agent</title>
        <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    """)

    html_parts.append(_create_dashboard_css())
    html_parts.append("</head><body>")

    # Container
    html_parts.append('<div class="container">')

    # Main content
    html_parts.append(view_content)

    # Footer
    html_parts.append(f"""
    <div class="footer">
        Investment MCP Agent Dashboard | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    </div>
    """)

    html_parts.append("</div></body></html>")

    return '\n'.join(html_parts)


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
    view: str = "daily",
    time_period: str = "all",
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate interactive HTML dashboard with portfolio visualizations.

    Args:
        view: Dashboard view - "daily", "performance", "transactions", "risk" (default: "daily")
        time_period: One of "7d", "30d", "90d", "1y", "all" (default: "all")
        force_regenerate: If True, regenerate even if recent dashboard exists

    Returns:
        dict: {
            "success": bool,
            "file_path": str (absolute path),
            "file_url": str (file:// URL),
            "snapshot_count": int,
            "date_range": {"start": str, "end": str},
            "view": str,
            "generated_at": str,
            "error": str (if success=False)
        }

    Raises:
        ValueError: If insufficient snapshots (need at least 2)
        IOError: If dashboard directory cannot be created
    """
    try:
        logger.info(f"Generating portfolio dashboard - view: {view}, period: {time_period}")

        # Validate view parameter
        valid_views = ["daily", "performance", "transactions", "risk"]
        if view not in valid_views:
            logger.warning(f"Invalid view '{view}', defaulting to 'daily'")
            view = "daily"

        # Get all snapshots
        all_snapshots = storage.get_all_snapshots()

        # Daily view only needs 1 snapshot (will show current status if no yesterday snapshot)
        min_snapshots = 1 if view == "daily" else 2

        if len(all_snapshots) < min_snapshots:
            return {
                "success": False,
                "error": f"Need at least {min_snapshots} snapshot(s) to generate dashboard (found {len(all_snapshots)})"
            }

        # Filter by time period
        snapshots = _filter_snapshots_by_period(all_snapshots, time_period)

        if len(snapshots) < min_snapshots:
            return {
                "success": False,
                "error": f"Need at least {min_snapshots} snapshot(s) in selected period (found {len(snapshots)})"
            }

        logger.info(f"Processing {len(snapshots)} snapshots for {view} view")

        # Route to appropriate view
        html_content = None

        if view == "daily":
            # Daily Overview - uses new view system
            from . import dashboard_views
            daily_view = dashboard_views.DailyOverviewView(snapshots, time_period)
            view_result = daily_view.generate()

            if not view_result.get("success"):
                return {
                    "success": False,
                    "error": view_result.get("error", "Failed to generate daily view")
                }

            # Wrap in full HTML page
            html_content = _wrap_view_html(view_result["html"], "Daily Overview", snapshots, time_period)

        else:
            # Performance/Transaction/Risk views - use legacy chart generation for now
            # Prepare data
            portfolio_df = _prepare_portfolio_timeseries(snapshots)
            category_df = _prepare_category_timeseries(snapshots)
            asset_df = _prepare_asset_timeseries(snapshots)

            # Get benchmark data
            spy_df, vt_df = _prepare_benchmark_data(snapshots)

            # Get top assets
            top_assets = _get_top_assets_by_value(snapshots[-1], n=10)

            # Generate charts based on view
            figures = {}

            if view == "performance":
                logger.info("Creating performance view charts...")
                figures["portfolio_value"] = _create_portfolio_value_chart(portfolio_df, spy_df, vt_df)
                figures["category_allocation"] = _create_category_allocation_chart(category_df)
                figures["asset_performance"] = _create_asset_performance_chart(asset_df, top_assets)
                figures["gainloss"] = _create_gainloss_chart(snapshots[-1])
                figures["hhi_trend"] = _create_hhi_trend_chart(snapshots)

            elif view == "transactions":
                logger.info("Creating transaction view charts...")
                figures["transactions"] = _create_quantity_changes_chart(snapshots)
                # TODO: Add realized gains chart when transaction data is available

            elif view == "risk":
                logger.info("Creating risk view charts...")
                figures["metrics"] = _create_metrics_dashboard(snapshots)
                # TODO: Add correlation heatmap and volatility charts when risk data is available

            # Generate HTML for legacy views
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
            "view": view,
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
