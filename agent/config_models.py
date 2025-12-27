"""
Configuration schema models using Pydantic v2.

Provides type-safe configuration with validation for the Investment MCP Agent.
All configuration is loaded from config.yaml with optional environment variable overrides.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal


class CurrencyCells(BaseModel):
    """
    Currency conversion cell locations in Google Sheets.
    
    These are USER-CONFIGURABLE and subject to change based on your sheet structure.
    Defaults are provided but can be overridden in config.yaml.
    """
    gbp_to_eur: str = Field(default="O2", description="Cell containing GBP to EUR rate")
    usd_to_eur: str = Field(default="O3", description="Cell containing USD to EUR rate")


class DataRanges(BaseModel):
    """
    Google Sheets data ranges for different asset types.
    
    These are USER-CONFIGURABLE and subject to change based on your sheet structure.
    Defaults match the standard template but can be customized in config.yaml.
    No validation is performed - if ranges are incorrect, Google Sheets API will return clear errors.
    """
    us_stocks: str = Field(default="A5:L19", description="Range for US stocks data")
    eu_stocks: str = Field(default="A20:L35", description="Range for EU stocks data")
    bonds: str = Field(default="A37:L39", description="Range for bonds data")
    etfs: str = Field(default="A40:L45", description="Range for ETFs data")
    pension: str = Field(default="A52:E53", description="Range for pension data")
    cash: str = Field(default="A58:B60", description="Range for cash positions data")


class GoogleSheetsConfig(BaseModel):
    """
    Google Sheets configuration.
    
    REQUIRED: Only sheet_id is required (external provider credential).
    OPTIONAL: sheet_name, currency_cells, and ranges are user-configurable with sensible defaults.
    """
    # REQUIRED: External provider credential
    sheet_id: str = Field(..., description="Google Sheet ID (REQUIRED)")
    
    # OPTIONAL: User-configurable data structure (defaults provided)
    sheet_name: str = Field(
        default="2025", 
        description="Active sheet tab name (optional, default: '2025')"
    )
    transactions_sheet_name: str = Field(
        default="Transactions",
        description="Transactions sheet tab name (optional, default: 'Transactions')"
    )
    transactions_range: str = Field(
        default="A2:E",
        description="Sell transactions data range (optional, default: 'A2:E')"
    )
    buy_transactions_range: str = Field(
        default="J2:M",
        description="Buy transactions data range (optional, default: 'J2:M')"
    )
    currency_cells: CurrencyCells = Field(
        default_factory=CurrencyCells,
        description="Currency conversion cell locations (optional, defaults provided)"
    )
    ranges: DataRanges = Field(
        default_factory=DataRanges,
        description="Data ranges for asset types (optional, defaults provided)"
    )
    
    @field_validator('sheet_id')
    @classmethod
    def validate_sheet_id(cls, v: str) -> str:
        """
        Validate sheet_id is set and not a placeholder.
        
        This is the ONLY required field for Google Sheets connection.
        All other fields (sheet_name, currency_cells, ranges) are optional user configurations.
        """
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
