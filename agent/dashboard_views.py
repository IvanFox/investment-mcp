"""
Dashboard View Orchestration

Coordinates components and charts into complete dashboard views.
Each view class generates HTML + charts for a specific dashboard perspective.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from . import storage
from . import daily_analysis
from . import dashboard_components as components

logger = logging.getLogger(__name__)


class DailyOverviewView:
    """
    Daily Overview - Quick check-in view optimized for seeing today's changes.
    """

    def __init__(self, snapshots: List[Dict[str, Any]], time_period: str = "7d"):
        """
        Initialize daily overview view.

        Args:
            snapshots: List of portfolio snapshots
            time_period: Time period for sparkline context
        """
        self.snapshots = snapshots
        self.time_period = time_period
        self.today_snapshot = snapshots[-1] if snapshots else None
        self.yesterday_snapshot = daily_analysis.get_yesterday_snapshot()

    def generate(self) -> Dict[str, Any]:
        """
        Generate daily overview view content.

        Returns:
            Dict with HTML content and metadata
        """
        if not self.today_snapshot:
            return {
                "success": False,
                "error": "No snapshot available for today"
            }

        # Check if we have yesterday's snapshot
        if not self.yesterday_snapshot:
            # Show current status without comparison
            return self._generate_current_status_only()

        # Calculate daily changes
        daily_data = daily_analysis.calculate_daily_changes(
            self.today_snapshot,
            self.yesterday_snapshot
        )

        # Calculate attribution
        attribution = daily_analysis.calculate_attribution(
            daily_data["asset_changes"],
            daily_data["total_change_eur"]
        )

        # Get win/loss ratio
        win_loss = daily_analysis.get_win_loss_ratio(daily_data["asset_changes"])

        # Build KPI cards
        kpi_cards = self._create_kpi_cards(daily_data, win_loss)

        # Build attribution table
        top_movers = attribution[:5]  # Top 5 movers
        attribution_table = components.create_attribution_table(top_movers)

        # Build 7-day sparkline
        sparkline = self._create_sparkline()

        # Build risk summary
        risk_summary = self._create_risk_summary()

        # Combine into HTML
        html_content = f'''
        <div class="daily-overview-view">
            {components.create_view_header("Daily Overview", "Portfolio changes since yesterday")}

            <div class="kpi-section">
                {components.create_grid(kpi_cards, columns=4)}
            </div>

            {components.create_section("Today's Movers", attribution_table)}

            <div class="context-section">
                <div class="sparkline-section">
                    {components.create_section("7-Day Trend", sparkline)}
                </div>
                <div class="risk-section">
                    {risk_summary}
                </div>
            </div>
        </div>
        '''

        return {
            "success": True,
            "html": html_content,
            "data": {
                "daily_changes": daily_data,
                "attribution": attribution,
                "win_loss": win_loss
            }
        }

    def _create_kpi_cards(
        self,
        daily_data: Dict[str, Any],
        win_loss: Dict[str, Any]
    ) -> List[str]:
        """Create KPI cards for daily overview."""
        cards = []

        # Card 1: Total Value
        cards.append(components.create_kpi_card(
            value=daily_data["today_value_eur"],
            label="Total Value",
            change_pct=daily_data["total_change_pct"],
            format_type="currency"
        ))

        # Card 2: Daily Change
        cards.append(components.create_kpi_card(
            value=daily_data["total_change_eur"],
            label="Today's Change",
            change_pct=daily_data["total_change_pct"],
            format_type="currency"
        ))

        # Card 3: Change Percentage
        cards.append(components.create_kpi_card(
            value=daily_data["total_change_pct"],
            label="Daily Return",
            format_type="percentage"
        ))

        # Card 4: Win/Loss Ratio
        win_ratio_text = f"{win_loss['winners']}/{win_loss['total']}"
        cards.append(components.create_kpi_card(
            value=win_loss['winners'],
            label="Winners",
            format_type="count",
            subtitle=f"{win_ratio_text} positions gaining"
        ))

        return cards

    def _create_sparkline(self) -> str:
        """Create 7-day portfolio value sparkline."""
        # Get last 7 days of snapshots
        recent_snapshots = self.snapshots[-7:] if len(self.snapshots) >= 7 else self.snapshots

        values = [s["total_value_eur"] for s in recent_snapshots]
        timestamps = [
            datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            for s in recent_snapshots
        ]

        return components.create_sparkline(values, timestamps, width=300, height=60)

    def _create_risk_summary(self) -> str:
        """Create one-line risk summary."""
        # Placeholder - will be enhanced with actual risk data
        return components.create_section(
            "Risk at a Glance",
            '<div class="risk-placeholder">Risk analysis will be displayed here</div>'
        )

    def _generate_current_status_only(self) -> Dict[str, Any]:
        """Generate view when no yesterday snapshot is available."""
        total_value = self.today_snapshot.get("total_value_eur", 0)

        # Count assets
        assets = self.today_snapshot.get("assets", [])
        asset_count = len([a for a in assets if a.get("current_value_eur", 0) > 0])

        html_content = f'''
        <div class="daily-overview-view">
            {components.create_view_header("Portfolio Status", "No previous snapshot for daily comparison")}

            <div class="kpi-section">
                {components.create_grid([
                    components.create_kpi_card(total_value, "Total Value", format_type="currency"),
                    components.create_kpi_card(asset_count, "Total Positions", format_type="count")
                ], columns=2)}
            </div>

            <div class="info-message">
                <p>Daily comparison requires a snapshot from yesterday.</p>
                <p>Run portfolio analysis tomorrow to see daily changes.</p>
            </div>
        </div>
        '''

        return {
            "success": True,
            "html": html_content,
            "data": {
                "current_value": total_value,
                "asset_count": asset_count
            }
        }


class PerformanceView:
    """
    Performance Analysis - Long-term portfolio trends and allocation analysis.
    """

    def __init__(self, snapshots: List[Dict[str, Any]], figures: Dict[str, Any]):
        """
        Initialize performance view.

        Args:
            snapshots: List of portfolio snapshots
            figures: Dict of Plotly figures from visualization.py
        """
        self.snapshots = snapshots
        self.figures = figures

    def generate(self) -> Dict[str, Any]:
        """
        Generate performance view content.

        Returns:
            Dict with HTML content and chart figures
        """
        # Build HTML with chart placeholders
        html_content = f'''
        <div class="performance-view">
            {components.create_view_header("Performance Analysis", "Portfolio trends and allocation")}

            {components.create_section("Portfolio Performance Hub", '<div id="chart-performance-hub"></div>')}

            {components.create_section("Allocation & Composition", '<div id="chart-allocation"></div>')}

            {components.create_section("Asset Deep Dive", '<div id="chart-asset-deep-dive"></div>')}

            {components.create_section("Risk & Correlation", '<div id="chart-risk-correlation"></div>')}
        </div>
        '''

        return {
            "success": True,
            "html": html_content,
            "figures": self.figures
        }


class TransactionView:
    """
    Transaction History - Trading activity and realized gains tracking.
    """

    def __init__(self, snapshots: List[Dict[str, Any]], figures: Dict[str, Any]):
        """
        Initialize transaction view.

        Args:
            snapshots: List of portfolio snapshots
            figures: Dict of Plotly figures
        """
        self.snapshots = snapshots
        self.figures = figures

    def generate(self) -> Dict[str, Any]:
        """
        Generate transaction view content.

        Returns:
            Dict with HTML content and chart figures
        """
        html_content = f'''
        <div class="transaction-view">
            {components.create_view_header("Transaction History", "Trading activity and realized gains")}

            {components.create_section("Transaction Timeline", '<div id="chart-transactions"></div>')}

            {components.create_section("Realized Gains Tracker", '<div id="chart-realized-gains"></div>')}
        </div>
        '''

        return {
            "success": True,
            "html": html_content,
            "figures": self.figures
        }


class RiskView:
    """
    Risk Analysis - Deep dive into portfolio risk metrics.
    """

    def __init__(self, snapshots: List[Dict[str, Any]], figures: Dict[str, Any]):
        """
        Initialize risk view.

        Args:
            snapshots: List of portfolio snapshots
            figures: Dict of Plotly figures
        """
        self.snapshots = snapshots
        self.figures = figures

    def generate(self) -> Dict[str, Any]:
        """
        Generate risk view content.

        Returns:
            Dict with HTML content and chart figures
        """
        html_content = f'''
        <div class="risk-view">
            {components.create_view_header("Risk Analysis", "Comprehensive risk assessment")}

            <div class="risk-grid">
                {components.create_section("Downside Risk", '<div id="chart-downside-risk"></div>')}

                {components.create_section("Volatility Analysis", '<div id="chart-volatility"></div>')}

                {components.create_section("Concentration Risk", '<div id="chart-concentration"></div>')}

                {components.create_section("Distribution Analysis", '<div id="chart-distribution"></div>')}
            </div>
        </div>
        '''

        return {
            "success": True,
            "html": html_content,
            "figures": self.figures
        }
