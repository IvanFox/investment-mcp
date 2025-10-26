"""
Generic Earnings Data Models

Provider-agnostic data structures for earnings events.
These models allow easy switching between different data providers
(Yahoo Finance, Alpha Vantage, Fintel, etc.)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EarningsEvent:
    """
    Generic earnings event data model.
    
    This model abstracts earnings data from any provider into a consistent format.
    """
    ticker: str
    company_name: str
    report_date: datetime
    estimate: Optional[float] = None
    fiscal_period: Optional[str] = None
    fiscal_year: Optional[int] = None
    source: str = "unknown"
    
    def days_until(self, from_date: Optional[datetime] = None) -> int:
        """
        Calculate days until earnings report.
        
        Args:
            from_date: Reference date (defaults to now in UTC)
            
        Returns:
            int: Number of days until the earnings report
        """
        if from_date is None:
            from datetime import timezone
            from_date = datetime.now(timezone.utc)
        
        # Ensure both dates are timezone-aware for comparison
        report_date = self.report_date
        if report_date.tzinfo is None:
            from datetime import timezone
            report_date = report_date.replace(tzinfo=timezone.utc)
        
        if from_date.tzinfo is None:
            from datetime import timezone
            from_date = from_date.replace(tzinfo=timezone.utc)
        
        delta = report_date - from_date
        return delta.days
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary format for API responses.
        
        Returns:
            dict: Dictionary representation of the earnings event
        """
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "report_date": self.report_date.isoformat(),
            "estimate": self.estimate,
            "fiscal_period": self.fiscal_period,
            "fiscal_year": self.fiscal_year,
            "source": self.source,
        }
