"""
Automation and Reporting

This module is responsible for creating human-readable reports.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def format_report_markdown(report_data: Dict[str, Any], current_total_value: float, current_snapshot: Optional[Dict[str, Any]] = None) -> str:
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


def format_positions_markdown(organized_data: Dict[str, Any]) -> str:
    """
    Formats organized position data as markdown report.
    
    Args:
        organized_data: Output from analysis.organize_positions_by_category()
        
    Returns:
        str: Markdown-formatted position report
    """
    try:
        timestamp = organized_data.get('timestamp', 'Unknown')
        total_value_eur = organized_data.get('total_value_eur', 0.0)
        categories = organized_data.get('categories', {})
        
        category_order = {
            'EU Stocks': ('🇪🇺', 1),
            'Pension': ('🏦', 2),
            'US Stocks': ('🇺🇸', 3),
            'Cash': ('💰', 4),
            'ETFs': ('📈', 5),
            'Bonds': ('📜', 6),
            'Other': ('📦', 7)
        }
        
        report_lines = []
        
        report_lines.append("# 💼 Current Portfolio Positions")
        report_lines.append("")
        report_lines.append(f"**Last Updated:** {timestamp}")
        report_lines.append(f"**Total Portfolio Value:** €{total_value_eur:,.2f}")
        report_lines.append("")
        
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: category_order.get(x[0], ('📦', 99))[1]
        )
        
        for category_name, category_data in sorted_categories:
            emoji = category_order.get(category_name, ('📦', 99))[0]
            total_value = category_data.get('total_value', 0.0)
            percentage = category_data.get('percentage', 0.0)
            positions = category_data.get('positions', [])
            
            report_lines.append(f"## {emoji} {category_name} (€{total_value:,.2f} - {percentage:.1f}%)")
            report_lines.append("")
            
            if not positions:
                report_lines.append("*No positions*")
                report_lines.append("")
                continue
            
            for i, position in enumerate(positions, 1):
                name = position.get('name', 'Unknown')
                quantity = position.get('quantity', 0.0)
                current_value = position.get('current_value_eur', 0.0)
                purchase_price = position.get('purchase_price_total_eur', 0.0)
                gain_loss_eur = position.get('gain_loss_eur', 0.0)
                gain_loss_percent = position.get('gain_loss_percent', 0.0)
                
                if category_name == 'Cash':
                    report_lines.append(f"{i}. **{name}** - €{current_value:,.2f}")
                elif quantity > 0:
                    report_lines.append(f"{i}. **{name}** - {quantity:,.0f} shares - €{current_value:,.2f}")
                else:
                    report_lines.append(f"{i}. **{name}** - €{current_value:,.2f}")
                
                if category_name not in ['Cash', 'Pension'] and purchase_price > 0:
                    gain_emoji = "📈" if gain_loss_eur >= 0 else "📉"
                    gain_sign = "+" if gain_loss_eur >= 0 else ""
                    report_lines.append(f"   - Purchase Cost: €{purchase_price:,.2f} | {gain_emoji} Gain/Loss: {gain_sign}€{gain_loss_eur:,.2f} ({gain_sign}{gain_loss_percent:.1f}%)")
                elif category_name == 'Pension' and purchase_price > 0:
                    gain_emoji = "📈" if gain_loss_eur >= 0 else "📉"
                    gain_sign = "+" if gain_loss_eur >= 0 else ""
                    report_lines.append(f"   - Initial Value: €{purchase_price:,.2f} | {gain_emoji} Change: {gain_sign}€{gain_loss_eur:,.2f} ({gain_sign}{gain_loss_percent:.1f}%)")
                
                report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("*Generated by Investment MCP Agent*")
        
        markdown_report = "\n".join(report_lines)
        
        logger.info("Successfully generated positions markdown report")
        return markdown_report
        
    except Exception as e:
        logger.error(f"Failed to format positions markdown: {e}")
        return f"""# 💼 Current Portfolio Positions

## ❌ Error
Failed to generate positions report: {str(e)}

*Generated by Investment MCP Agent*"""


def format_risk_report_markdown(risk_data: Dict[str, Any]) -> str:
    """
    Format risk analysis results as markdown report.
    
    Args:
        risk_data: Risk analysis results from risk_analysis.analyze_portfolio_risk()
        
    Returns:
        str: Formatted markdown risk report
    """
    try:
        if not risk_data.get('success', False):
            error_msg = risk_data.get('error', 'Unknown error')
            return f"""# 📊 Portfolio Risk Analysis

## ❌ Error
{error_msg}

Please ensure:
- Alpha Vantage API key is configured
- Ticker mappings are complete
- Portfolio has sufficient history

*Risk analysis generated by Investment MCP Agent*"""
        
        report_lines = []
        
        report_lines.append("# 📊 Portfolio Risk Analysis")
        report_lines.append("")
        
        analysis_date = risk_data.get('analysis_date', 'Unknown')
        portfolio_value = risk_data.get('portfolio_value_eur', 0)
        assets_analyzed = risk_data.get('assets_analyzed', 0)
        total_assets = risk_data.get('total_assets', 0)
        
        report_lines.append(f"**Analysis Date:** {analysis_date[:10]}")
        report_lines.append(f"**Portfolio Value:** €{portfolio_value:,.2f}")
        report_lines.append(f"**Assets Analyzed:** {assets_analyzed} of {total_assets}")
        report_lines.append(f"**Analysis Period:** {risk_data.get('analysis_period_days', 252)} trading days")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        beta = risk_data.get('beta')
        var_metrics = risk_data.get('var_metrics', {})
        concentration = risk_data.get('concentration', {})
        volatility = risk_data.get('volatility', {})
        downside_metrics = risk_data.get('downside_metrics', {})
        
        report_lines.append("## 📈 Executive Summary")
        report_lines.append("")
        report_lines.append("| Metric | Value | Rating |")
        report_lines.append("|--------|-------|--------|")
        
        if beta is not None:
            beta_rating = _get_beta_rating(beta)
            report_lines.append(f"| Portfolio Beta | {beta:.2f} | {beta_rating} |")
        
        var_95 = var_metrics.get('var_95_historical')
        if var_95 is not None:
            var_value_eur = portfolio_value * var_95
            var_rating = _get_var_rating(var_95)
            report_lines.append(f"| VaR (95%, 1-day) | -€{abs(var_value_eur):,.0f} ({var_95*100:.2f}%) | {var_rating} |")
        
        hhi = concentration.get('hhi', 0)
        hhi_rating = _get_hhi_rating(hhi)
        report_lines.append(f"| Concentration (HHI) | {hhi:.3f} | {hhi_rating} |")
        
        max_dd = downside_metrics.get('max_drawdown_pct')
        if max_dd is not None:
            dd_rating = _get_drawdown_rating(max_dd)
            report_lines.append(f"| Max Drawdown | {max_dd:.1f}% | {dd_rating} |")
        
        annual_vol = volatility.get('portfolio_annual_volatility_pct')
        if annual_vol is not None:
            vol_rating = _get_volatility_rating(annual_vol)
            report_lines.append(f"| Annual Volatility | {annual_vol:.1f}% | {vol_rating} |")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        if beta is not None:
            report_lines.append("## 🎯 Market Sensitivity (Beta)")
            report_lines.append("")
            report_lines.append(f"**Portfolio Beta: {beta:.2f}** (vs. S&P 500)")
            report_lines.append("")
            
            if beta > 1.0:
                diff = (beta - 1.0) * 100
                report_lines.append(f"- Your portfolio is **{diff:.0f}% more volatile** than the market")
            elif beta < 1.0:
                diff = (1.0 - beta) * 100
                report_lines.append(f"- Your portfolio is **{diff:.0f}% less volatile** than the market")
            else:
                report_lines.append("- Your portfolio moves in line with the market")
            
            report_lines.append(f"- 1% market move → Expected {abs(beta):.2f}% portfolio move")
            
            if beta > 1.15:
                report_lines.append("- ⚠️ High volatility: Greater potential returns but increased risk")
            elif beta < 0.85:
                report_lines.append("- ✅ Lower volatility: More stable but potentially lower returns")
            
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")
        
        if var_metrics:
            report_lines.append("## 💰 Value at Risk (VaR)")
            report_lines.append("")
            
            var_95_hist = var_metrics.get('var_95_historical')
            var_99_hist = var_metrics.get('var_99_historical')
            
            if var_95_hist is not None:
                report_lines.append("| Confidence | 1-Day VaR | 1-Week VaR | 1-Month VaR |")
                report_lines.append("|------------|-----------|------------|-------------|")
                
                var_95_1d = portfolio_value * var_95_hist
                var_95_1w = portfolio_value * var_95_hist * (5 ** 0.5)
                var_95_1m = portfolio_value * var_95_hist * (20 ** 0.5)
                report_lines.append(f"| 95% | -€{abs(var_95_1d):,.0f} ({var_95_hist*100:.2f}%) | -€{abs(var_95_1w):,.0f} ({var_95_hist*100*(5**0.5):.2f}%) | -€{abs(var_95_1m):,.0f} ({var_95_hist*100*(20**0.5):.2f}%) |")
                
                if var_99_hist is not None:
                    var_99_1d = portfolio_value * var_99_hist
                    var_99_1w = portfolio_value * var_99_hist * (5 ** 0.5)
                    var_99_1m = portfolio_value * var_99_hist * (20 ** 0.5)
                    report_lines.append(f"| 99% | -€{abs(var_99_1d):,.0f} ({var_99_hist*100:.2f}%) | -€{abs(var_99_1w):,.0f} ({var_99_hist*100*(5**0.5):.2f}%) | -€{abs(var_99_1m):,.0f} ({var_99_hist*100*(20**0.5):.2f}%) |")
                
                report_lines.append("")
                report_lines.append(f"**Interpretation:** At 95% confidence, you won't lose more than €{abs(var_95_1d):,.0f} in a single day")
                report_lines.append("")
                report_lines.append("---")
                report_lines.append("")
        
        if concentration:
            report_lines.append("## 🎲 Concentration Risk")
            report_lines.append("")
            hhi = concentration.get('hhi', 0)
            hhi_label = _get_hhi_label(hhi)
            report_lines.append(f"**HHI Score: {hhi:.3f}** - {hhi_label}")
            report_lines.append("")
            
            report_lines.append("| Metric | Value | Status |")
            report_lines.append("|--------|-------|--------|")
            
            largest_pct = concentration.get('largest_position_pct', 0)
            largest_name = concentration.get('largest_position_name', 'Unknown')
            largest_status = "✅ Safe" if largest_pct < 15 else "⚠️ High" if largest_pct < 25 else "❌ Very High"
            report_lines.append(f"| Largest Single Position | {largest_pct:.1f}% ({largest_name}) | {largest_status} |")
            
            top_5_pct = concentration.get('top_5_concentration_pct', 0)
            top_5_status = "✅ Safe" if top_5_pct < 50 else "⚠️ Moderate" if top_5_pct < 70 else "❌ High"
            report_lines.append(f"| Top 5 Holdings | {top_5_pct:.1f}% | {top_5_status} |")
            
            num_positions = concentration.get('num_positions', 0)
            pos_status = "✅ Good" if num_positions >= 15 else "⚠️ Low" if num_positions >= 8 else "❌ Very Low"
            report_lines.append(f"| Total Positions | {num_positions} | {pos_status} |")
            
            report_lines.append("")
            
            top_holdings = concentration.get('top_holdings', [])
            if top_holdings:
                report_lines.append("**Top 5 Holdings:**")
                for i, holding in enumerate(top_holdings, 1):
                    name = holding.get('name', 'Unknown')
                    weight = holding.get('weight_pct', 0)
                    report_lines.append(f"{i}. {name}: {weight:.1f}%")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        correlation_data = risk_data.get('correlation')
        if correlation_data:
            high_corrs = correlation_data.get('high_correlations', [])
            
            if high_corrs:
                report_lines.append("## 🔗 High Correlations Detected")
                report_lines.append("")
                report_lines.append("The following asset pairs move together (correlation > 0.7):")
                report_lines.append("")
                
                for corr in high_corrs[:10]:
                    asset1 = corr.get('asset1', '')
                    asset2 = corr.get('asset2', '')
                    corr_val = corr.get('correlation', 0)
                    report_lines.append(f"- **{asset1}** ↔ **{asset2}**: {corr_val:.2f}")
                
                report_lines.append("")
                report_lines.append("⚠️ High correlations may reduce diversification benefits")
                report_lines.append("")
                report_lines.append("---")
                report_lines.append("")
        
        exposure = risk_data.get('exposure', {})
        if exposure:
            sectors = exposure.get('sectors', {})
            geography = exposure.get('geography', {})
            
            if sectors:
                report_lines.append("## 🌍 Exposure Analysis")
                report_lines.append("")
                report_lines.append("### Sector Breakdown")
                report_lines.append("")
                report_lines.append("| Sector | Value | % | Assets |")
                report_lines.append("|--------|-------|---|--------|")
                
                for sector, data in sectors.items():
                    value = data.get('value', 0)
                    pct = data.get('percentage', 0)
                    count = data.get('count', 0)
                    report_lines.append(f"| {sector} | €{value:,.0f} | {pct:.1f}% | {count} |")
                
                report_lines.append("")
            
            if geography:
                report_lines.append("### Geographic Breakdown")
                report_lines.append("")
                report_lines.append("| Region | Value | % | Assets |")
                report_lines.append("|--------|-------|---|--------|")
                
                for region, data in geography.items():
                    value = data.get('value', 0)
                    pct = data.get('percentage', 0)
                    count = data.get('count', 0)
                    report_lines.append(f"| {region} | €{value:,.0f} | {pct:.1f}% | {count} |")
                
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        if volatility:
            by_category = volatility.get('by_category', {})
            
            if by_category:
                report_lines.append("## 📉 Volatility by Asset Class")
                report_lines.append("")
                report_lines.append("| Asset Class | Annual Volatility |")
                report_lines.append("|-------------|-------------------|")
                
                for category, vol in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"| {category} | {vol:.1f}% |")
                
                report_lines.append("")
                report_lines.append("---")
                report_lines.append("")
        
        if downside_metrics:
            report_lines.append("## ⬇️ Downside Risk Metrics")
            report_lines.append("")
            report_lines.append("| Metric | Value | Interpretation |")
            report_lines.append("|--------|-------|----------------|")
            
            sortino = downside_metrics.get('sortino_ratio')
            if sortino is not None:
                sortino_interp = "Excellent" if sortino > 2 else "Good" if sortino > 1 else "Fair" if sortino > 0.5 else "Poor"
                report_lines.append(f"| Sortino Ratio | {sortino:.2f} | {sortino_interp} risk-adjusted returns |")
            
            max_dd = downside_metrics.get('max_drawdown_pct')
            if max_dd is not None:
                report_lines.append(f"| Maximum Drawdown | {max_dd:.1f}% | Largest historical decline |")
            
            downside_dev = downside_metrics.get('downside_deviation')
            if downside_dev is not None:
                report_lines.append(f"| Downside Deviation | {downside_dev:.1f}% | Volatility of negative returns |")
            
            cvar = downside_metrics.get('cvar_95_pct')
            if cvar is not None:
                report_lines.append(f"| CVaR (95%) | {cvar:.1f}% | Average loss beyond VaR |")
            
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")
        
        report_lines.append("*Risk analysis generated by Investment MCP Agent*")
        report_lines.append("*Data source: Alpha Vantage API*")
        
        markdown_report = "\n".join(report_lines)
        
        logger.info("Successfully generated risk analysis markdown report")
        return markdown_report
        
    except Exception as e:
        logger.error(f"Failed to format risk report markdown: {e}")
        return f"""# 📊 Portfolio Risk Analysis

## ❌ Error
Failed to generate risk report: {str(e)}

*Risk analysis generated by Investment MCP Agent*"""


def _get_beta_rating(beta: float) -> str:
    """Get rating for beta value."""
    if beta > 1.3:
        return "❌ Very High Volatility"
    elif beta > 1.15:
        return "⚠️ High Volatility"
    elif beta > 0.85:
        return "✅ Moderate"
    else:
        return "✅ Low Volatility"


def _get_var_rating(var: float) -> str:
    """Get rating for VaR value."""
    var_pct = abs(var * 100)
    if var_pct > 3:
        return "❌ High Risk"
    elif var_pct > 2:
        return "⚠️ Moderate Risk"
    else:
        return "✅ Low Risk"


def _get_hhi_rating(hhi: float) -> str:
    """Get rating for HHI value."""
    if hhi > 0.25:
        return "❌ High Concentration"
    elif hhi > 0.15:
        return "⚠️ Moderate Concentration"
    else:
        return "✅ Well Diversified"


def _get_hhi_label(hhi: float) -> str:
    """Get label for HHI value."""
    if hhi > 0.25:
        return "Highly Concentrated ❌"
    elif hhi > 0.15:
        return "Moderately Concentrated ⚠️"
    else:
        return "Well Diversified ✅"


def _get_drawdown_rating(dd: float) -> str:
    """Get rating for maximum drawdown."""
    dd_abs = abs(dd)
    if dd_abs > 20:
        return "❌ High"
    elif dd_abs > 10:
        return "⚠️ Moderate"
    else:
        return "✅ Low"


def _get_volatility_rating(vol: float) -> str:
    """Get rating for volatility."""
    if vol > 25:
        return "❌ Very High"
    elif vol > 18:
        return "⚠️ High"
    elif vol > 12:
        return "⚠️ Moderate"
    else:
        return "✅ Low"