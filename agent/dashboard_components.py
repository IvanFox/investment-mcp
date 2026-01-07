"""
Dashboard UI Components

Reusable HTML/CSS components for building portfolio dashboard views.
"""

import logging
from typing import Dict, List, Any, Optional

import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def create_kpi_card(
    value: float,
    label: str,
    change_pct: Optional[float] = None,
    format_type: str = "currency",
    subtitle: Optional[str] = None
) -> str:
    """
    Generate a KPI card HTML component.

    Args:
        value: Main metric value to display
        label: Card label (e.g., "Total Value")
        change_pct: Optional percentage change (for color coding)
        format_type: How to format value - "currency", "percentage", "count", "ratio"
        subtitle: Optional subtitle text

    Returns:
        HTML string for KPI card
    """
    # Format value based on type
    if format_type == "currency":
        formatted_value = f"€{value:,.0f}"
    elif format_type == "percentage":
        formatted_value = f"{value:+.1f}%"
    elif format_type == "count":
        formatted_value = f"{int(value)}"
    elif format_type == "ratio":
        formatted_value = str(value)
    else:
        formatted_value = str(value)

    # Determine color class based on change
    color_class = ""
    if change_pct is not None:
        if change_pct > 0:
            color_class = "positive"
        elif change_pct < 0:
            color_class = "negative"
        else:
            color_class = "neutral"

    # Build subtitle HTML if provided
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="kpi-subtitle">{subtitle}</div>'

    # Build change indicator if provided
    change_html = ""
    if change_pct is not None and format_type == "currency":
        change_icon = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "="
        change_html = f'''
        <div class="kpi-change {color_class}">
            <span class="change-icon">{change_icon}</span>
            <span class="change-value">{change_pct:+.1f}%</span>
        </div>
        '''

    return f'''
    <div class="kpi-card {color_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{formatted_value}</div>
        {change_html}
        {subtitle_html}
    </div>
    '''


def create_summary_table(
    data: List[Dict[str, Any]],
    columns: List[Dict[str, str]]
) -> str:
    """
    Create a generic summary table.

    Args:
        data: List of dicts with row data
        columns: List of {key, label} dicts defining columns

    Returns:
        HTML string for table
    """
    if not data:
        return '<div class="table-empty">No data available</div>'

    # Build header
    header_cells = "".join([f'<th>{col["label"]}</th>' for col in columns])
    header = f'<thead><tr>{header_cells}</tr></thead>'

    # Build rows
    rows = []
    for row_data in data:
        cells = []
        for col in columns:
            value = row_data.get(col["key"], "")
            cell_class = col.get("class", "")
            cells.append(f'<td class="{cell_class}">{value}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')

    body = f'<tbody>{"".join(rows)}</tbody>'

    return f'''
    <div class="summary-table-container">
        <table class="summary-table">
            {header}
            {body}
        </table>
    </div>
    '''


def create_attribution_table(movers: List[Dict[str, Any]]) -> str:
    """
    Create attribution analysis table showing top movers.

    Args:
        movers: List of dicts with {name, change_eur, change_pct, contribution_pct, is_gainer}

    Returns:
        HTML string for attribution table
    """
    if not movers:
        return '<div class="attribution-empty">No significant movers today</div>'

    rows = []
    for mover in movers:
        icon = "▲" if mover["is_gainer"] else "▼"
        row_class = "gainer" if mover["is_gainer"] else "loser"
        change_class = "positive" if mover["is_gainer"] else "negative"

        name = mover["name"]
        change_eur = abs(mover["change_eur"])
        change_pct = mover["change_pct"]
        contribution = abs(mover["contribution_pct"])

        row = f'''
        <tr class="attribution-row {row_class}">
            <td class="attr-icon">{icon}</td>
            <td class="attr-name">{name}</td>
            <td class="attr-change {change_class}">
                <div class="change-eur">€{change_eur:,.2f}</div>
                <div class="change-pct">{change_pct:+.1f}%</div>
            </td>
            <td class="attr-contribution">
                <div class="contribution-bar-container">
                    <div class="contribution-bar {row_class}" style="width: {min(contribution, 100)}%"></div>
                    <span class="contribution-text">{contribution:.0f}%</span>
                </div>
            </td>
        </tr>
        '''
        rows.append(row)

    return f'''
    <div class="attribution-table-container">
        <table class="attribution-table">
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
    '''


def create_sparkline(
    values: List[float],
    timestamps: Optional[List[str]] = None,
    width: int = 200,
    height: int = 50
) -> str:
    """
    Create a small sparkline chart (embedded SVG or Plotly).

    Args:
        values: List of numeric values
        timestamps: Optional list of timestamp strings for hover
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        HTML string containing sparkline (Plotly div)
    """
    if not values or len(values) < 2:
        return '<div class="sparkline-empty">Insufficient data</div>'

    try:
        # Create minimal Plotly line chart
        fig = go.Figure()

        x_values = timestamps if timestamps else list(range(len(values)))

        fig.add_trace(go.Scatter(
            x=x_values,
            y=values,
            mode="lines",
            line=dict(color="#3B82F6", width=2),
            fill="tozeroy",
            fillcolor="rgba(59, 130, 246, 0.1)",
            hovertemplate="%{y:,.0f}<extra></extra>" if not timestamps else "%{x}<br>€%{y:,.0f}<extra></extra>"
        ))

        fig.update_layout(
            width=width,
            height=height,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False,
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        # Convert to HTML div
        sparkline_html = fig.to_html(include_plotlyjs=False, div_id=f"sparkline-{id(values)}")

        return f'<div class="sparkline-container">{sparkline_html}</div>'

    except Exception as e:
        logger.error(f"Error creating sparkline: {e}")
        return f'<div class="sparkline-error">Error: {e}</div>'


def create_stat_card(
    value: str,
    label: str,
    icon: str = "",
    color_class: str = ""
) -> str:
    """
    Create a simple stat card (alternative to KPI card).

    Args:
        value: Value to display (pre-formatted)
        label: Card label
        icon: Optional emoji/icon
        color_class: Optional CSS class for coloring

    Returns:
        HTML string for stat card
    """
    icon_html = f'<div class="stat-icon">{icon}</div>' if icon else ''

    return f'''
    <div class="stat-card {color_class}">
        {icon_html}
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    '''


def create_view_header(
    title: str,
    subtitle: Optional[str] = None,
    last_updated: Optional[str] = None
) -> str:
    """
    Create a view header section.

    Args:
        title: Main title
        subtitle: Optional subtitle
        last_updated: Optional timestamp string

    Returns:
        HTML string for header
    """
    subtitle_html = f'<div class="view-subtitle">{subtitle}</div>' if subtitle else ''
    updated_html = f'<div class="view-updated">Last updated: {last_updated}</div>' if last_updated else ''

    return f'''
    <div class="view-header">
        <h1 class="view-title">{title}</h1>
        {subtitle_html}
        {updated_html}
    </div>
    '''


def create_section(title: str, content: str, collapsible: bool = False) -> str:
    """
    Create a section container with optional collapsible functionality.

    Args:
        title: Section title
        content: HTML content for section body
        collapsible: Whether section can be collapsed

    Returns:
        HTML string for section
    """
    collapse_class = "collapsible" if collapsible else ""
    collapse_btn = '<button class="collapse-btn">▼</button>' if collapsible else ''

    return f'''
    <div class="section {collapse_class}">
        <div class="section-header">
            <h2 class="section-title">{title}</h2>
            {collapse_btn}
        </div>
        <div class="section-body">
            {content}
        </div>
    </div>
    '''


def create_grid(items: List[str], columns: int = 4) -> str:
    """
    Create a responsive grid layout.

    Args:
        items: List of HTML strings to place in grid
        columns: Number of columns for desktop view

    Returns:
        HTML string for grid
    """
    return f'''
    <div class="grid" style="grid-template-columns: repeat({columns}, 1fr);">
        {"".join(items)}
    </div>
    '''
