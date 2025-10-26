"""
Abstract Earnings Data Provider Interface

Defines the contract for earnings data providers, allowing easy switching
between different data sources (Yahoo Finance, Alpha Vantage, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from .earnings_models import EarningsEvent


class EarningsDataProvider(ABC):
    """
    Abstract base class for earnings data providers.
    
    Implementations must provide methods to fetch earnings calendar data
    and individual ticker earnings dates.
    """
    
    @abstractmethod
    def fetch_earnings_calendar(self, horizon_months: int = 3) -> List[EarningsEvent]:
        """
        Fetch earnings calendar for specified time horizon.
        
        Args:
            horizon_months: Number of months to look ahead (default: 3)
            
        Returns:
            list: List of EarningsEvent objects
            
        Raises:
            Exception: If API request fails or data cannot be fetched
        """
        pass
    
    @abstractmethod
    def fetch_earnings_for_ticker(self, ticker: str) -> Optional[EarningsEvent]:
        """
        Fetch next earnings date for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "WISE.L")
            
        Returns:
            EarningsEvent or None: Next earnings event for the ticker, or None if not found
            
        Raises:
            Exception: If API request fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the name of the data provider.
        
        Returns:
            str: Provider name (e.g., "Yahoo Finance", "Alpha Vantage")
        """
        pass
