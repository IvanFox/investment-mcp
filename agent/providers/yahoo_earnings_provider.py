"""
Yahoo Finance Earnings Data Provider

Implementation of earnings data provider using Yahoo Finance API via yfinance library.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import yfinance as yf

from ..earnings_provider import EarningsDataProvider
from ..earnings_models import EarningsEvent

logger = logging.getLogger(__name__)


class YahooEarningsProvider(EarningsDataProvider):
    """
    Yahoo Finance implementation of earnings data provider.
    
    Uses the yfinance library to fetch earnings calendar data from Yahoo Finance.
    No API key required - free data access.
    """
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "Yahoo Finance"
    
    def fetch_earnings_for_ticker(self, ticker: str) -> Optional[EarningsEvent]:
        """
        Fetch next earnings date for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
            
        Returns:
            EarningsEvent or None: Next earnings event, or None if not found
            
        Raises:
            Exception: If API request fails
        """
        try:
            logger.info(f"Fetching earnings date for {ticker} from Yahoo Finance...")
            
            stock = yf.Ticker(ticker)
            
            # Get company info for name
            company_name = ticker
            try:
                info = stock.info
                company_name = info.get('longName') or info.get('shortName') or ticker
            except Exception as e:
                logger.warning(f"Could not fetch company name for {ticker}: {e}")
            
            # Get earnings dates
            calendar = stock.calendar
            
            if calendar is None or not calendar:
                logger.warning(f"No earnings calendar data available for {ticker}")
                return None
            
            # Yahoo Finance returns a dict with earnings date
            # Try to get 'Earnings Date' field
            earnings_date = None
            
            if 'Earnings Date' in calendar:
                earnings_dates = calendar['Earnings Date']
                # If it's a list, take the first (next upcoming)
                if isinstance(earnings_dates, list) and len(earnings_dates) > 0:
                    earnings_date = earnings_dates[0]
                else:
                    earnings_date = earnings_dates
            
            if earnings_date is None:
                logger.warning(f"Could not parse earnings date from calendar for {ticker}")
                return None
            
            # Convert to datetime
            import datetime as dt
            if isinstance(earnings_date, dt.date) and not isinstance(earnings_date, datetime):
                # Convert date to datetime
                earnings_date = datetime.combine(earnings_date, datetime.min.time())
            elif hasattr(earnings_date, 'to_pydatetime'):
                earnings_date = earnings_date.to_pydatetime()  # type: ignore
            elif isinstance(earnings_date, str):
                # Try to parse string date
                earnings_date = datetime.fromisoformat(earnings_date.replace('Z', '+00:00'))
            
            # Ensure timezone aware
            if hasattr(earnings_date, 'tzinfo') and earnings_date.tzinfo is None:  # type: ignore
                earnings_date = earnings_date.replace(tzinfo=timezone.utc)  # type: ignore
            
            # Get earnings estimate if available
            estimate = None
            try:
                if 'Earnings Average' in calendar:
                    estimate_val = calendar['Earnings Average']
                    if estimate_val:
                        estimate = float(estimate_val)
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Could not parse earnings estimate for {ticker}: {e}")
            
            logger.info(f"Successfully fetched earnings date for {ticker}: {earnings_date}")
            
            return EarningsEvent(
                ticker=ticker,
                company_name=company_name,
                report_date=earnings_date,
                estimate=estimate,
                source="yahoo_finance"
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch earnings for {ticker} from Yahoo Finance: {e}")
            raise
    
    def fetch_earnings_calendar(self, horizon_months: int = 3) -> List[EarningsEvent]:
        """
        Fetch earnings calendar for specified time horizon.
        
        Note: Yahoo Finance does not provide a bulk earnings calendar endpoint.
        This method is designed to be called with a list of specific tickers
        from the portfolio.
        
        Args:
            horizon_months: Number of months to look ahead (default: 3)
            
        Returns:
            list: Empty list (use fetch_earnings_for_tickers instead)
        """
        logger.warning(
            "Yahoo Finance does not provide bulk earnings calendar. "
            "Use fetch_earnings_for_tickers() with your portfolio tickers instead."
        )
        return []
    
    def fetch_earnings_for_tickers(
        self, 
        tickers: List[str], 
        horizon_months: int = 3
    ) -> List[EarningsEvent]:
        """
        Fetch earnings dates for a list of tickers.
        
        This is the preferred method for Yahoo Finance provider since it doesn't
        offer a bulk calendar endpoint.
        
        Args:
            tickers: List of stock ticker symbols
            horizon_months: Number of months to look ahead (default: 3)
            
        Returns:
            list: List of EarningsEvent objects within the time horizon
        """
        earnings_events = []
        now = datetime.now(timezone.utc)
        horizon_date = now + timedelta(days=horizon_months * 30)
        
        for ticker in tickers:
            try:
                event = self.fetch_earnings_for_ticker(ticker)
                if event and now <= event.report_date <= horizon_date:
                    earnings_events.append(event)
            except Exception as e:
                logger.error(f"Failed to fetch earnings for {ticker}: {e}")
                continue
        
        # Sort by date
        earnings_events.sort(key=lambda e: e.report_date)
        
        logger.info(
            f"Fetched earnings for {len(earnings_events)} out of {len(tickers)} tickers "
            f"within {horizon_months} month horizon"
        )
        
        return earnings_events
