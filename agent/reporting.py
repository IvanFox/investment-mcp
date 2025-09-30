"""
Automation and Reporting

This module is responsible for creating human-readable reports.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def format_report_markdown(report_data: Dict[str, Any], current_total_value: float, current_snapshot: Dict[str, Any] = None) -> str:
    """
    Converts the analysis data object into a formatted Markdown string.
    
    Args:
        report_data: The dictionary returned by analysis.compare_snapshots
        current_total_value: The total value from the current snapshot
        current_snapshot: The current snapshot data for portfolio breakdown
        
    Returns:
        str: A multi-line string in Markdown format
    """
    try:
        # Extract data from report
        total_change_eur = report_data.get('total_value_change_eur', 0.0)
        total_change_percent = report_data.get('total_value_change_percent', 0.0)
        top_movers = report_data.get('top_movers', [])
        bottom_movers = report_data.get('bottom_movers', [])
        new_positions = report_data.get('new_positions', [])
        sold_positions = report_data.get('sold_positions', [])
        
        # Build the markdown report
        report_lines = []
        
        # Header
        report_lines.append("# 📊 Weekly Portfolio Performance Report")
        report_lines.append("")
        
        # Portfolio Summary
        report_lines.append("## 💰 Portfolio Summary")
        report_lines.append(f"**Current Total Value:** €{current_total_value:,.2f}")
        
        # Format change with appropriate emoji
        change_emoji = "📈" if total_change_eur >= 0 else "📉"
        change_sign = "+" if total_change_eur >= 0 else ""
        
        report_lines.append(f"**Weekly Change:** {change_emoji} {change_sign}€{total_change_eur:,.2f} ({change_sign}{total_change_percent:.2f}%)")
        report_lines.append("")
        
        # Top Movers (Gainers)
        if top_movers:
            report_lines.append("## 🚀 Top Performers")
            for i, mover in enumerate(top_movers, 1):
                name = mover.get('name', 'Unknown')
                change = mover.get('change_eur', 0.0)
                report_lines.append(f"{i}. **{name}**: +€{change:,.2f}")
            report_lines.append("")
        
        # Bottom Movers (Losers)
        if bottom_movers:
            report_lines.append("## 📉 Underperformers")
            for i, mover in enumerate(bottom_movers, 1):
                name = mover.get('name', 'Unknown')
                change = mover.get('change_eur', 0.0)
                report_lines.append(f"{i}. **{name}**: €{change:,.2f}")
            report_lines.append("")
        
        # New Positions
        if new_positions:
            report_lines.append("## 🆕 New Positions")
            for position in new_positions:
                name = position.get('name', 'Unknown')
                quantity = position.get('quantity', 0.0)
                value = position.get('current_value_eur', 0.0)
                report_lines.append(f"- **{name}**: {quantity:,.0f} shares, €{value:,.2f}")
            report_lines.append("")
        
        # Sold Positions
        if sold_positions:
            report_lines.append("## 💸 Sold Positions")
            total_realized = sum(pos.get('realized_gain_loss_eur', 0.0) for pos in sold_positions)
            
            for position in sold_positions:
                name = position.get('name', 'Unknown')
                gain_loss = position.get('realized_gain_loss_eur', 0.0)
                gain_loss_emoji = "💰" if gain_loss >= 0 else "💔"
                gain_loss_sign = "+" if gain_loss >= 0 else ""
                report_lines.append(f"- **{name}**: {gain_loss_emoji} {gain_loss_sign}€{gain_loss:,.2f}")
            
            report_lines.append("")
            total_emoji = "💰" if total_realized >= 0 else "💔"
            total_sign = "+" if total_realized >= 0 else ""
            report_lines.append(f"**Total Realized P&L:** {total_emoji} {total_sign}€{total_realized:,.2f}")
            report_lines.append("")
        
        # Footer with portfolio breakdown
        report_lines.append("---")
        
        # Add portfolio breakdown by category
        if current_snapshot and 'assets' in current_snapshot:
            categories = {}
            for asset in current_snapshot['assets']:
                category = asset.get('category', 'Unknown')
                if category not in categories:
                    categories[category] = 0
                categories[category] += asset.get('current_value_eur', 0)
            
            if categories:
                report_lines.append("\n## 📊 Portfolio Allocation")
                for category, value in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    percentage = (value / current_total_value * 100) if current_total_value > 0 else 0
                    report_lines.append(f"- **{category}**: €{value:,.2f} ({percentage:.1f}%)")
                report_lines.append("")
        
        report_lines.append("*Report generated automatically by Investment MCP Agent*")
        
        # Join all lines
        markdown_report = "\n".join(report_lines)
        
        logger.info("Successfully generated markdown report")
        return markdown_report
        
    except Exception as e:
        logger.error(f"Failed to format markdown report: {e}")
        # Return a basic error report
        return f"""# 📊 Weekly Portfolio Performance Report

## ❌ Error
Failed to generate report: {str(e)}

*Report generated automatically by Investment MCP Agent*"""


def format_report_summary(report_data: Dict[str, Any], current_total_value: float) -> str:
    """
    Creates a brief text summary of the portfolio changes.
    
    Args:
        report_data: The dictionary returned by analysis.compare_snapshots
        current_total_value: The total value from the current snapshot
        
    Returns:
        str: A brief summary string
    """
    try:
        total_change_eur = report_data.get('total_value_change_eur', 0.0)
        total_change_percent = report_data.get('total_value_change_percent', 0.0)
        new_count = len(report_data.get('new_positions', []))
        sold_count = len(report_data.get('sold_positions', []))
        
        change_word = "gained" if total_change_eur >= 0 else "lost"
        change_sign = "+" if total_change_eur >= 0 else ""
        
        summary = f"Portfolio {change_word} {change_sign}€{abs(total_change_eur):,.2f} ({change_sign}{total_change_percent:.2f}%) this week. "
        summary += f"Current value: €{current_total_value:,.2f}. "
        
        if new_count > 0:
            summary += f"{new_count} new position{'s' if new_count != 1 else ''}. "
        
        if sold_count > 0:
            summary += f"{sold_count} position{'s' if sold_count != 1 else ''} sold."
        
        return summary.strip()
        
    except Exception as e:
        logger.error(f"Failed to format summary: {e}")
        return f"Portfolio report summary unavailable due to error: {str(e)}"