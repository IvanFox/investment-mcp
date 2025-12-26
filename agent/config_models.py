"""
Configuration schema models using Pydantic v2.

Provides type-safe configuration with validation for the Investment MCP Agent.
All configuration is loaded from config.yaml with optional environment variable overrides.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal


class CurrencyCells(BaseModel):
    """Currency conversion cell locations in Google Sheets."""
    gbp_to_eur: str = "O2"
    usd_to_eur: str = "O3"


class DataRanges(BaseModel):
    """Google Sheets data ranges for different asset types."""
    us_stocks: str = "A5:L19"
    eu_stocks: str = "A20:L35"
    bonds: str = "A37:L39"
    etfs: str = "A40:L45"
    pension: str = "A52:E53"
    cash: str = "A58:B60"


class GoogleSheetsConfig(BaseModel):
    """Google Sheets configuration."""
    sheet_id: str = Field(..., description="Google Sheet ID (required)")
    sheet_name: str = "2025"
    currency_cells: CurrencyCells = Field(default_factory=CurrencyCells)
    ranges: DataRanges = Field(default_factory=DataRanges)
    
    @field_validator('sheet_id')
    @classmethod
    def validate_sheet_id(cls, v: str) -> str:
        """Validate sheet_id is set and not a placeholder."""
        if not v or v.strip() == "" or "YOUR_SHEET_ID" in v.upper():
            raise ValueError(
                "sheet_id must be set to your actual Google Sheet ID. "
                "Find it in your sheet URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
            )
        return v


class GCPStorageConfig(BaseModel):
    """GCP Cloud Storage configuration."""
    bucket_name: str = "investment_snapshots"
    region: str = "europe-north1"
    blob_name: str = "portfolio_history.json"
    
    @field_validator('bucket_name')
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate GCS bucket naming rules."""
        if not v or len(v) < 3 or len(v) > 63:
            raise ValueError("bucket_name must be 3-63 characters long")
        if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError("bucket_name can only contain letters, numbers, hyphens, underscores, and dots")
        return v


class LocalStorageConfig(BaseModel):
    """Local file storage configuration."""
    data_dir: str = "."
    history_file: str = "portfolio_history.json"


class StorageConfig(BaseModel):
    """Storage backend configuration."""
    backend: Literal["hybrid", "gcp", "local"] = "hybrid"
    gcp: GCPStorageConfig = Field(default_factory=GCPStorageConfig)
    local: LocalStorageConfig = Field(default_factory=LocalStorageConfig)


class AlphaVantageConfig(BaseModel):
    """Alpha Vantage API configuration."""
    rate_limit_delay: int = Field(default=12, ge=1, description="Seconds between API calls")
    cache_ttl: int = Field(default=86400, ge=0, description="Cache duration in seconds")


class FintelConfig(BaseModel):
    """Fintel API configuration."""
    base_url: str = "https://api.fintel.io/public"


class YahooFinanceConfig(BaseModel):
    """Yahoo Finance API configuration."""
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")


class APIConfig(BaseModel):
    """API configurations."""
    alpha_vantage: AlphaVantageConfig = Field(default_factory=AlphaVantageConfig)
    fintel: FintelConfig = Field(default_factory=FintelConfig)
    yahoo_finance: YahooFinanceConfig = Field(default_factory=YahooFinanceConfig)


class RiskAnalysisConfig(BaseModel):
    """Risk analysis configuration."""
    analysis_period_days: int = Field(default=252, ge=1, description="Trading days for analysis")
    var_confidence_levels: List[float] = Field(default=[0.95, 0.99])
    market_benchmark: str = "^GSPC"
    
    @field_validator('var_confidence_levels')
    @classmethod
    def validate_var_levels(cls, v: List[float]) -> List[float]:
        """Validate VaR confidence levels are between 0 and 1."""
        for level in v:
            if not 0 < level < 1:
                raise ValueError(f"VaR confidence level {level} must be between 0 and 1")
        return v


class ConcentrationConfig(BaseModel):
    """Concentration risk thresholds."""
    high_single_position: int = Field(default=25, ge=0, le=100)
    moderate_single_position: int = Field(default=15, ge=0, le=100)
    high_top_5: int = Field(default=70, ge=0, le=100)
    moderate_top_5: int = Field(default=50, ge=0, le=100)


class InsiderTradingConfig(BaseModel):
    """Insider trading analysis configuration."""
    lookback_days: int = Field(default=90, ge=1)
    bullish_ratio: float = Field(default=2.0, gt=0)


class ShortVolumeConfig(BaseModel):
    """Short volume analysis configuration."""
    default_days: int = Field(default=30, ge=1)
    high_risk_threshold: int = Field(default=40, ge=0, le=100)
    medium_risk_threshold: int = Field(default=30, ge=0, le=100)


class AnalysisConfig(BaseModel):
    """Analysis settings."""
    risk: RiskAnalysisConfig = Field(default_factory=RiskAnalysisConfig)
    concentration: ConcentrationConfig = Field(default_factory=ConcentrationConfig)
    insider_trading: InsiderTradingConfig = Field(default_factory=InsiderTradingConfig)
    short_volume: ShortVolumeConfig = Field(default_factory=ShortVolumeConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class InvestmentConfig(BaseModel):
    """
    Root configuration model for Investment MCP Agent.
    
    All configuration must be provided via config.yaml.
    Environment variables can override specific values.
    
    Environment variable overrides:
    - INVESTMENT_GCP_BUCKET: Override storage.gcp.bucket_name
    - INVESTMENT_SHEET_ID: Override google_sheets.sheet_id
    - INVESTMENT_STORAGE_BACKEND: Override storage.backend
    - INVESTMENT_LOG_LEVEL: Override logging.level
    """
    google_sheets: GoogleSheetsConfig
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ticker_mappings: Dict[str, str] = Field(..., description="Stock name to ticker symbol mappings")
    apis: APIConfig = Field(default_factory=APIConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @field_validator('ticker_mappings')
    @classmethod
    def validate_ticker_mappings(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate ticker_mappings is not empty."""
        if not v:
            raise ValueError(
                "ticker_mappings cannot be empty. "
                "Add at least one mapping: 'Stock Name': 'TICKER'"
            )
        return v
    
    model_config = {
        "extra": "allow",  # Allow extra fields for future expansion
        "str_strip_whitespace": True,  # Strip whitespace from strings
    }
