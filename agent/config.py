"""
Configuration management for Investment MCP Agent.

Loads and validates config.yaml with environment variable overrides.
Uses Pydantic v2 for schema validation with fail-fast behavior.
"""

import os
import yaml
from typing import Optional, Dict
import logging

from pydantic import ValidationError
from .config_models import InvestmentConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.yaml"
_config: Optional[InvestmentConfig] = None


def load_config(config_path: str = CONFIG_FILE) -> InvestmentConfig:
    """
    Load and validate configuration from YAML file.
    
    Applies environment variable overrides after loading YAML.
    Fails fast if configuration is invalid or missing.
    
    Args:
        config_path: Path to config.yaml (default: "config.yaml")
        
    Returns:
        InvestmentConfig: Validated configuration object
        
    Raises:
        FileNotFoundError: If config.yaml doesn't exist
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML syntax is invalid
    """
    global _config
    
    if _config is not None:
        return _config
    
    # Check file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"❌ CRITICAL: Configuration file not found: {config_path}\n\n"
            f"The application requires config.yaml to run.\n\n"
            f"To create config.yaml:\n"
            f"  1. Copy the example configuration:\n"
            f"     cp config.yaml.example config.yaml\n\n"
            f"  2. Edit config.yaml with your settings:\n"
            f"     - Add your Google Sheet ID\n"
            f"     - Configure ticker mappings for your stocks\n"
            f"     - Set storage backend (hybrid/gcp/local)\n\n"
            f"Application will not start without valid configuration."
        )
    
    try:
        # Load YAML
        logger.info(f"Loading configuration from {config_path}...")
        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        if not yaml_data:
            raise ValueError(f"Configuration file is empty: {config_path}")
        
        # Apply environment variable overrides
        yaml_data = _apply_env_overrides(yaml_data)
        
        # Validate with Pydantic
        config = InvestmentConfig(**yaml_data)
        
        _config = config
        logger.info(f"✅ Configuration loaded and validated from {config_path}")
        logger.info(f"   Using GCP bucket: {config.storage.gcp.bucket_name}")
        logger.info(f"   Using storage backend: {config.storage.backend}")
        logger.info(f"   Ticker mappings: {len(config.ticker_mappings)}")
        
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"❌ CRITICAL: Invalid YAML syntax in {config_path}\n\n"
            f"Error: {e}\n\n"
            f"Please fix the YAML syntax errors above.\n"
            f"Application will not start with invalid YAML."
        )
    except ValidationError as e:
        raise ValueError(
            f"❌ CRITICAL: Configuration validation failed.\n\n"
            f"Errors in {config_path}:\n{e}\n\n"
            f"Please fix the configuration errors above.\n"
            f"Application will not start with invalid configuration."
        )


def _apply_env_overrides(yaml_data: dict) -> dict:
    """
    Apply environment variable overrides to configuration.
    
    Supported environment variables:
    - INVESTMENT_GCP_BUCKET: Override storage.gcp.bucket_name
    - INVESTMENT_SHEET_ID: Override google_sheets.sheet_id
    - INVESTMENT_STORAGE_BACKEND: Override storage.backend
    - INVESTMENT_LOG_LEVEL: Override logging.level
    
    Args:
        yaml_data: Loaded YAML data
        
    Returns:
        dict: YAML data with environment variable overrides applied
    """
    
    # GCP Bucket override
    if "INVESTMENT_GCP_BUCKET" in os.environ:
        bucket_name = os.environ["INVESTMENT_GCP_BUCKET"]
        yaml_data.setdefault("storage", {}).setdefault("gcp", {})["bucket_name"] = bucket_name
        logger.info(f"   ENV override: GCP bucket = {bucket_name}")
    
    # Sheet ID override
    if "INVESTMENT_SHEET_ID" in os.environ:
        sheet_id = os.environ["INVESTMENT_SHEET_ID"]
        yaml_data.setdefault("google_sheets", {})["sheet_id"] = sheet_id
        logger.info(f"   ENV override: Sheet ID = {sheet_id[:20]}...")
    
    # Storage backend override
    if "INVESTMENT_STORAGE_BACKEND" in os.environ:
        backend = os.environ["INVESTMENT_STORAGE_BACKEND"]
        yaml_data.setdefault("storage", {})["backend"] = backend
        logger.info(f"   ENV override: Storage backend = {backend}")
    
    # Log level override
    if "INVESTMENT_LOG_LEVEL" in os.environ:
        log_level = os.environ["INVESTMENT_LOG_LEVEL"]
        yaml_data.setdefault("logging", {})["level"] = log_level
        logger.info(f"   ENV override: Log level = {log_level}")
    
    return yaml_data


def get_config() -> InvestmentConfig:
    """
    Get cached configuration or load if not yet loaded.
    
    Returns:
        InvestmentConfig: Validated configuration object
    """
    if _config is None:
        return load_config()
    return _config


def reload_config(config_path: str = CONFIG_FILE) -> InvestmentConfig:
    """
    Force reload configuration from file.
    
    Useful for testing or when configuration changes at runtime.
    
    Args:
        config_path: Path to config.yaml
        
    Returns:
        InvestmentConfig: Validated configuration object
    """
    global _config
    _config = None
    return load_config(config_path)


# ============================================================================
# Convenience accessor functions
# ============================================================================

def get_sheet_id() -> str:
    """Get Google Sheet ID."""
    return get_config().google_sheets.sheet_id


def get_sheet_name() -> str:
    """Get Google Sheet name (tab)."""
    return get_config().google_sheets.sheet_name


def get_ticker_mappings() -> Dict[str, str]:
    """Get ticker mappings dictionary."""
    return get_config().ticker_mappings


def get_ticker_for_stock(stock_name: str) -> Optional[str]:
    """
    Get ticker symbol for a stock name.
    
    Args:
        stock_name: Stock name as it appears in portfolio
        
    Returns:
        str: Ticker symbol or None if not mapped
    """
    return get_config().ticker_mappings.get(stock_name)


def get_gcp_bucket_name() -> str:
    """Get GCP storage bucket name."""
    return get_config().storage.gcp.bucket_name


def get_storage_backend() -> str:
    """Get storage backend type (hybrid/gcp/local)."""
    return get_config().storage.backend


def get_log_level() -> str:
    """Get logging level."""
    return get_config().logging.level
