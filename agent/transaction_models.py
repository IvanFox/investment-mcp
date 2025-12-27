"""
Transaction Data Models

Defines data structures for buy and sell transactions.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SellTransaction(BaseModel):
    """
    Represents a single sell transaction from Transactions sheet.
    
    Attributes:
        date: Transaction date (contractual/trade date)
        asset_name: Name of asset sold (exact match with portfolio)
        quantity: Number of shares sold
        sell_price_per_unit: Price per unit in original currency
        currency: Original currency (USD, GBP, or EUR)
        sell_price_per_unit_eur: Price per unit converted to EUR
        total_value_eur: Total transaction value in EUR
    """
    
    date: datetime
    asset_name: str
    quantity: float
    sell_price_per_unit: float
    currency: Literal["USD", "GBP", "EUR"]
    sell_price_per_unit_eur: float
    total_value_eur: float
    
    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse DD/MM/YYYY format from sheet."""
        if isinstance(v, str):
            return datetime.strptime(v, '%d/%m/%Y')
        return v
    
    @field_validator('asset_name')
    @classmethod
    def validate_asset_name(cls, v):
        """Ensure asset name is not empty."""
        if not v or not v.strip():
            raise ValueError("Asset name cannot be empty")
        return v.strip()
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Ensure quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class BuyTransaction(BaseModel):
    """
    Represents a single buy transaction from Transactions sheet.
    
    Attributes:
        date: Transaction date (contractual/trade date)
        asset_name: Name of asset purchased (exact match with portfolio)
        quantity: Number of shares purchased
        purchase_price_per_unit: Price per unit in original currency
        currency: Original currency (USD, GBP, or EUR)
        purchase_price_per_unit_eur: Price per unit converted to EUR
        total_value_eur: Total transaction value in EUR
    """
    
    date: datetime
    asset_name: str
    quantity: float
    purchase_price_per_unit: float
    currency: Literal["USD", "GBP", "EUR"]
    purchase_price_per_unit_eur: float
    total_value_eur: float
    
    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse DD/MM/YYYY format from sheet."""
        if isinstance(v, str):
            return datetime.strptime(v, '%d/%m/%Y')
        return v
    
    @field_validator('asset_name')
    @classmethod
    def validate_asset_name(cls, v):
        """Ensure asset name is not empty."""
        if not v or not v.strip():
            raise ValueError("Asset name cannot be empty")
        return v.strip()
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Ensure quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v
