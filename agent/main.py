"""
Main Entry Point for Investment MCP Agent

This is the main entry point where the fastmcp agent is defined and 
the scheduled task is orchestrated.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastmcp import FastMCP

# Import our modules
from . import sheets_connector
from . import analysis
from . import storage
from . import reporting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the MCP agent
mcp = FastMCP("Investment Portfolio Agent")


@mcp.tool()
def run_portfolio_analysis() -> str:
    """
    Manually trigger a portfolio analysis run.
    
    Returns:
        str: Analysis result message
    """
    try:
        return _run_weekly_analysis()
    except Exception as e:
        error_msg = f"Portfolio analysis failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def get_portfolio_status() -> str:
    """
    Get the current portfolio status from the latest snapshot.
    
    Returns:
        str: Current portfolio status
    """
    try:
        latest_snapshot = storage.get_latest_snapshot()
        
        if not latest_snapshot:
            return "No portfolio snapshots available. Run analysis first."
        
        timestamp = latest_snapshot.get('timestamp', 'Unknown time')
        total_value = latest_snapshot.get('total_value_eur', 0.0)
        asset_count = len(latest_snapshot.get('assets', []))
        
        return f"""📊 Latest Portfolio Status
        
**Last Updated:** {timestamp}
**Total Value:** €{total_value:,.2f}
**Number of Assets:** {asset_count}

Run portfolio analysis to generate a new snapshot and comparison report."""
        
    except Exception as e:
        error_msg = f"Failed to get portfolio status: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def get_portfolio_history_summary() -> str:
    """
    Get a summary of the portfolio history.
    
    Returns:
        str: Portfolio history summary
    """
    try:
        all_snapshots = storage.get_all_snapshots()
        
        if not all_snapshots:
            return "No portfolio history available."
        
        first_snapshot = all_snapshots[0]
        latest_snapshot = all_snapshots[-1]
        
        first_date = first_snapshot.get('timestamp', 'Unknown')
        latest_date = latest_snapshot.get('timestamp', 'Unknown')
        first_value = first_snapshot.get('total_value_eur', 0.0)
        latest_value = latest_snapshot.get('total_value_eur', 0.0)
        
        total_change = latest_value - first_value
        total_change_percent = (total_change / first_value * 100) if first_value > 0 else 0
        
        change_emoji = "📈" if total_change >= 0 else "📉"
        change_sign = "+" if total_change >= 0 else ""
        
        return f"""📈 Portfolio History Summary

**Total Snapshots:** {len(all_snapshots)}
**First Snapshot:** {first_date}
**Latest Snapshot:** {latest_date}

**Performance Since Start:**
- Initial Value: €{first_value:,.2f}
- Current Value: €{latest_value:,.2f}
- Total Change: {change_emoji} {change_sign}€{total_change:,.2f} ({change_sign}{total_change_percent:.2f}%)"""
        
    except Exception as e:
        error_msg = f"Failed to get portfolio history: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def get_upcoming_events() -> str:
    """
     Get upcoming earnings reports for portfolio stocks.
     
     Returns upcoming earnings reports within the next 2 months, sorted chronologically.
     Events are fetched from Alpha Vantage API and matched against portfolio stocks
     using the ticker_mapping.json file.
    
    Returns:
        str: Formatted list of upcoming events or error message
    """
    try:
        from . import events_tracker
        
        logger.info("Fetching upcoming events for portfolio...")
        
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        result = events_tracker.get_portfolio_upcoming_events(normalized_data)
        
        if not result.get("success", False):
            if result.get("unmapped_stocks"):
                error_lines = [result.get("error", "Error")]
                error_lines.extend(result.get("unmapped_stocks", []))
                error_lines.append("")
                error_lines.append(result.get("action", ""))
                return "\n".join(error_lines)
            else:
                return result.get("error", "Unknown error occurred")
        
        events = result.get("events", [])
        
        if not events:
            return """📅 Upcoming Earnings Reports

No upcoming earnings reports found within the next 2 months for your portfolio stocks.

**Note:** Ensure that:
1. All portfolio stocks are mapped in ticker_mapping.json
2. Your stocks have upcoming earnings announcements
3. Alpha Vantage API key is properly configured"""
        
        output_lines = ["📅 Upcoming Earnings Reports (Next 2 Months)", "", ""]
        
        for event in events:
            event_type = event.get("type", "")
            ticker = event.get("ticker", "")
            company = event.get("company_name", "")
            date = event.get("date", "")
            days_until = event.get("days_until", 0)
            
            output_lines.append(f"**{event_type}**")
            output_lines.append(f"- Ticker: {ticker}")
            output_lines.append(f"- Company: {company}")
            output_lines.append(f"- Date: {date} ({days_until} days)")
            
            if event_type == "Earnings Report":
                estimate = event.get("estimate")
                if estimate:
                    output_lines.append(f"- Estimate: {estimate}")
            
            output_lines.append("")
        
        output_lines.append(f"**Summary:**")
        output_lines.append(f"- Total Reports: {result.get('total_events', 0)}")
        output_lines.append(f"- Earnings Reports: {result.get('earnings_count', 0)}")
        output_lines.append(f"- Last Updated: {result.get('as_of', 'Unknown')}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        error_msg = f"Failed to get upcoming events: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def _run_weekly_analysis() -> str:
    """
    Core function that performs the weekly portfolio analysis workflow.
    
    Returns:
        str: Result message
    """
    try:
        logger.info("Starting weekly portfolio analysis...")
        
        # Get the previous snapshot
        previous_snapshot = storage.get_latest_snapshot()
        
        # Fetch and normalize current portfolio data
        logger.info("Fetching portfolio data from Google Sheets...")
        raw_data = sheets_connector.fetch_portfolio_data()
        normalized_data = sheets_connector.parse_and_normalize_data(raw_data)
        
        # Create new snapshot
        logger.info("Creating portfolio snapshot...")
        current_snapshot = analysis.create_portfolio_snapshot(normalized_data)
        
        # Save the snapshot immediately
        storage.save_snapshot(current_snapshot)
        logger.info("Snapshot saved successfully")
        
        # If we have a previous snapshot, perform comparison
        if previous_snapshot:
            logger.info("Performing week-over-week comparison...")
            report_data = analysis.compare_snapshots(current_snapshot, previous_snapshot)
            
            # Generate markdown report
            current_total_value = current_snapshot.get('total_value_eur', 0.0)
            markdown_report = reporting.format_report_markdown(report_data, current_total_value, current_snapshot)
            
            logger.info("Weekly analysis completed successfully")
            return markdown_report
        else:
            # First run
            current_total_value = current_snapshot.get('total_value_eur', 0.0)
            first_run_message = f"""# 📊 Portfolio Tracking Initialized

**Initial Portfolio Value:** €{current_total_value:,.2f}
**Assets Tracked:** {len(normalized_data)}
**Timestamp:** {current_snapshot.get('timestamp', 'Unknown')}

This is the first snapshot of your portfolio. Weekly comparison reports will be available starting next week.

---
*Report generated automatically by Investment MCP Agent*"""
            
            logger.info("First portfolio snapshot created successfully")
            return first_run_message
            
    except Exception as e:
        error_msg = f"Weekly analysis failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


if __name__ == "__main__":
    # For testing purposes, you can run the analysis directly
    try:
        result = _run_weekly_analysis()
        print(result)
    except Exception as e:
        print(f"Error: {e}")