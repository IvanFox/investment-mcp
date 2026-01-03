"""
Google Sheets Data Extraction Module

This module is solely responsible for connecting to the Google Sheets API,
fetching, and normalizing the raw portfolio data.
"""

import json
import subprocess
import os
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials
import logging

from . import config

logger = logging.getLogger(__name__)


# ============================================================================
# Dynamic range getters - read from config instead of hardcoded constants
# ============================================================================

def _get_sheet_name() -> str:
    """Get active sheet name from config."""
    return config.get_sheet_name()


def _get_asset_ranges() -> Dict[str, str]:
    """Get asset ranges from config with sheet name prefix."""
    ranges = config.get_data_ranges()
    sheet_name = _get_sheet_name()
    return {
        "stocks_us": f"{sheet_name}!{ranges.us_stocks}",
        "stocks_eu": f"{sheet_name}!{ranges.eu_stocks}",
        "bonds": f"{sheet_name}!{ranges.bonds}",
        "etfs": f"{sheet_name}!{ranges.etfs}",
    }


def _get_rates_range() -> str:
    """Get currency rates range from config."""
    cells = config.get_currency_cells()
    sheet_name = _get_sheet_name()
    # Construct range from first cell to last cell
    return f"{sheet_name}!{cells.gbp_to_eur}:{cells.usd_to_eur}"


def _get_pension_range() -> str:
    """Get pension range from config."""
    ranges = config.get_data_ranges()
    sheet_name = _get_sheet_name()
    return f"{sheet_name}!{ranges.pension}"


def _get_cash_range() -> str:
    """Get cash range from config."""
    ranges = config.get_data_ranges()
    sheet_name = _get_sheet_name()
    return f"{sheet_name}!{ranges.cash}"


def parse_currency_value(value_str):
    """
    Parse a currency string like '$50.00', '€0.62', '£215.00' and return the numeric value.

    Args:
        value_str: String containing currency symbol and amount

    Returns:
        float: Numeric value without currency symbol
    """
    if not value_str:
        return 0.0

    # Convert to string and clean
    value_str = str(value_str).strip()

    if not value_str:
        return 0.0

    # Remove currency symbols and common formatting
    # Remove: $, €, £, ¥, and other common symbols, commas, spaces
    clean_value = value_str

    # Remove currency symbols
    for symbol in ["$", "€", "£", "¥", "¢", "₹", "₽", "¤"]:
        clean_value = clean_value.replace(symbol, "")

    # Remove commas and spaces
    clean_value = clean_value.replace(",", "").replace(" ", "")

    # Handle empty string after cleaning
    if not clean_value or clean_value == "-":
        return 0.0

    try:
        return float(clean_value)
    except (ValueError, TypeError):
        return 0.0


def load_credentials_from_keychain():
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-a",
                "mcp-portfolio-agent",
                "-s",
                "google-sheets-credentials",
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Strip whitespace
        hex_str = result.stdout.strip()

        # Decode from hexadecimal to bytes
        credentials_bytes = bytes.fromhex(hex_str)

        # Decode bytes to string (UTF-8)
        credentials_str = credentials_bytes.decode("utf-8")

        return json.loads(credentials_str)

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to retrieve credentials from Keychain: {e.stderr}")
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode credentials: {e}")


def get_sheets_service():
    """
    Authenticates with the Google API using credentials.json and returns a service object.
    Supports both API key authentication and Service Account authentication.

    Returns:
        googleapiclient.discovery.Resource: The Google Sheets API service object
    """
    try:
        # Load credentials from credentials.json
        # with open("credentials.json", "r") as f:
        #     credentials_data = json.load(f)
        credentials_data = load_credentials_from_keychain()

        # Check if this is a service account JSON file
        if "type" in credentials_data and credentials_data["type"] == "service_account":
            logger.info("Using Service Account authentication")
            from google.oauth2 import service_account

            # Create credentials from service account info
            credentials = service_account.Credentials.from_service_account_info(
                credentials_data,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )

            # Build service with service account credentials
            service = build("sheets", "v4", credentials=credentials)
            logger.info(
                "Successfully authenticated with Google Sheets API using Service Account"
            )
            return service

        else:
            # Fall back to API key authentication
            api_key = credentials_data.get("googleApiKey")
            if not api_key:
                raise ValueError(
                    "Neither service account credentials nor API key found in credentials.json"
                )

            logger.info("Using API key authentication")
            # Build service with API key
            service = build("sheets", "v4", developerKey=api_key)
            logger.info(
                "Successfully authenticated with Google Sheets API using API key"
            )
            return service

    except Exception as e:
        logger.error(f"Failed to authenticate with Google Sheets API: {e}")
        raise


def fetch_portfolio_data() -> Dict[str, Any]:
    """
    Fetches all required raw data from the spreadsheet.

    Returns:
        dict: Contains the raw values for rates and assets
        Example:
        {
            "rates": [[1.1589], [0.8490]],
            "assets": {
                "stocks_us": [["Wise", "10003", ...], ["Intel Corp", "55", ...]],
                "stocks_eu": [["Artea bank", "2100", ...]]
            }
        }
    """
    try:
        service = get_sheets_service()

        # Get sheet ID from config
        cfg = config.get_config()
        spreadsheet_id = cfg.google_sheets.sheet_id
        
        if not spreadsheet_id:
            raise ValueError("Sheet ID not found in configuration")

        # Get ranges from config
        asset_ranges = _get_asset_ranges()
        rates_range = _get_rates_range()
        pension_range = _get_pension_range()
        cash_range = _get_cash_range()

        # Prepare batch request for all ranges
        ranges = (
            [rates_range] + list(asset_ranges.values()) + [pension_range, cash_range]
        )

        # Batch get all ranges
        result = (
            service.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
            .execute()
        )

        value_ranges = result.get("valueRanges", [])

        if len(value_ranges) < len(ranges):
            raise ValueError("Not all ranges returned data")

        # Extract rates (first range)
        rates = value_ranges[0].get("values", [])

        # Extract asset data (ranges 1 to len(asset_ranges))
        assets = {}
        for i, (category, _) in enumerate(asset_ranges.items()):
            assets[category] = value_ranges[i + 1].get("values", [])

        # Extract pension data (range after asset ranges)
        pension_data = value_ranges[len(asset_ranges) + 1].get("values", [])

        # Extract cash data (last range)
        cash_data = value_ranges[len(asset_ranges) + 2].get("values", [])

        raw_data = {
            "rates": rates,
            "assets": assets,
            "pension": pension_data,
            "cash": cash_data,
        }

        logger.info(
            f"Successfully fetched portfolio data: {len(assets)} asset categories, pension data, cash data"
        )
        return raw_data

    except Exception as e:
        logger.error(f"Failed to fetch portfolio data: {e}")
        raise


def parse_and_normalize_data(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Takes the raw data from fetch_portfolio_data and transforms it into a clean,
    standardized list of asset dictionaries.

    Args:
        raw_data: The dictionary returned by fetch_portfolio_data

    Returns:
        list[dict]: List of normalized asset dictionaries

    Each asset dictionary has the schema:
    {
        "name": str,
        "quantity": float,
        "purchase_price_total_eur": float,
        "current_value_eur": float,
        "category": str
    }
    """
    try:
        # Extract currency rates
        rates_data = raw_data.get("rates", [])

        # Default rates (1.0 for EUR, will be overridden if available)
        gbp_to_eur = 1.1589  # Default
        usd_to_eur = 0.8490  # Default

        if len(rates_data) >= 2:
            try:
                gbp_to_eur = float(rates_data[0][0]) if rates_data[0] else gbp_to_eur
                usd_to_eur = float(rates_data[1][0]) if rates_data[1] else usd_to_eur
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse currency rates, using defaults: {e}")

        logger.info(
            f"Using currency rates - GBP/EUR: {gbp_to_eur}, USD/EUR: {usd_to_eur}"
        )

        normalized_assets = []

        # Process each asset category
        for category, rows in raw_data.get("assets", {}).items():
            for row in rows:
                try:
                    # Skip empty rows or rows without name
                    if (
                        not row
                        or len(row) < 4
                        or not row[0]
                        or str(row[0]).strip() == ""
                    ):
                        continue

                    name = str(row[0]).strip()

                    # Parse quantity
                    try:
                        quantity = float(row[1]) if len(row) > 1 and row[1] else 0.0
                    except (ValueError, TypeError):
                        quantity = 0.0

                    # Parse purchase price per unit (column D = index 3, with currency formatting)
                    try:
                        purchase_price_per_unit = (
                            parse_currency_value(row[3]) if len(row) > 3 else 0.0
                        )
                    except (ValueError, TypeError):
                        purchase_price_per_unit = 0.0

                    # Parse current value per unit (column E = index 4, with currency formatting)
                    try:
                        current_price_per_unit = (
                            parse_currency_value(row[4]) if len(row) > 4 else 0.0
                        )
                    except (ValueError, TypeError):
                        current_price_per_unit = 0.0

                    # Parse daily change percentage (column H = index 7)
                    try:
                        daily_change_pct = 0.0
                        if len(row) > 7 and row[7]:
                            # Handle percentage format (e.g., "5.2%", "-3.1%", or just "5.2")
                            change_str = str(row[7]).strip().replace('%', '').replace(',', '.')
                            daily_change_pct = float(change_str) if change_str and change_str not in ['-', 'N/A', '#N/A'] else 0.0
                    except (ValueError, TypeError):
                        daily_change_pct = 0.0

                    # Determine currency and conversion based on the original currency in the data
                    currency_symbol = ""
                    if len(row) > 3 and row[3]:
                        raw_purchase = str(row[3]).strip()
                        if raw_purchase.startswith("$"):
                            currency_symbol = "USD"
                        elif raw_purchase.startswith("£"):
                            currency_symbol = "GBP"
                        elif raw_purchase.startswith("€"):
                            currency_symbol = "EUR"

                    # Apply currency conversion to per-unit prices
                    if currency_symbol == "USD":
                        # Convert USD to EUR
                        purchase_price_per_unit_eur = (
                            purchase_price_per_unit * usd_to_eur
                        )
                        current_price_per_unit_eur = current_price_per_unit * usd_to_eur
                    elif currency_symbol == "GBP":
                        # Convert GBP to EUR
                        purchase_price_per_unit_eur = (
                            purchase_price_per_unit * gbp_to_eur
                        )
                        current_price_per_unit_eur = current_price_per_unit * gbp_to_eur
                    else:
                        # Assume EUR or no conversion needed
                        purchase_price_per_unit_eur = purchase_price_per_unit
                        current_price_per_unit_eur = current_price_per_unit

                    # Calculate total amounts by multiplying by quantity
                    purchase_price_total_eur = purchase_price_per_unit_eur * quantity
                    current_value_eur = current_price_per_unit_eur * quantity

                    # Determine category name for reporting
                    category_map = {
                        "stocks_us": "US Stocks",
                        "stocks_eu": "EU Stocks",
                        "bonds": "Bonds",
                        "etfs": "ETFs",
                    }
                    category_name = category_map.get(category, category)

                    asset_dict = {
                        "name": name,
                        "quantity": quantity,
                        "purchase_price_total_eur": round(purchase_price_total_eur, 2),
                        "current_value_eur": round(current_value_eur, 2),
                        "category": category_name,
                        "daily_change_pct": round(daily_change_pct, 2),
                    }

                    normalized_assets.append(asset_dict)

                except Exception as e:
                    logger.warning(
                        f"Skipping row due to parsing error: {row}, error: {e}"
                    )
                    continue

        # Process pension data
        pension_data = raw_data.get("pension", [])
        for row in pension_data:
            try:
                # Skip empty rows or rows without pension scheme name
                if not row or len(row) < 1 or not row[0] or str(row[0]).strip() == "":
                    continue

                pension_name = str(row[0]).strip()

                # Parse current value (column E = index 4)
                try:
                    current_value = (
                        parse_currency_value(row[4]) if len(row) > 4 else 0.0
                    )
                except (ValueError, TypeError):
                    current_value = 0.0

                if current_value > 0:  # Only include if there's a value
                    asset_dict = {
                        "name": pension_name,
                        "quantity": 1.0,  # Pension is treated as 1 unit
                        "purchase_price_total_eur": current_value,  # For pension, purchase = current (no gain/loss tracking)
                        "current_value_eur": current_value,
                        "category": "Pension",
                    }
                    normalized_assets.append(asset_dict)

            except Exception as e:
                logger.warning(
                    f"Skipping pension row due to parsing error: {row}, error: {e}"
                )
                continue

        # Process cash data
        cash_data = raw_data.get("cash", [])
        for row in cash_data:
            try:
                # Skip empty rows or rows without currency name
                if not row or len(row) < 2 or not row[0] or str(row[0]).strip() == "":
                    continue

                currency_name = str(row[0]).strip()

                # Parse cash amount (column B = index 1)
                try:
                    cash_amount = parse_currency_value(row[1]) if len(row) > 1 else 0.0
                except (ValueError, TypeError):
                    cash_amount = 0.0

                if cash_amount > 0:  # Only include if there's a value
                    # Determine currency conversion
                    cash_amount_eur = cash_amount
                    if "USD" in currency_name.upper() or "$" in currency_name:
                        cash_amount_eur = cash_amount * usd_to_eur
                    elif "GBP" in currency_name.upper() or "£" in currency_name:
                        cash_amount_eur = cash_amount * gbp_to_eur
                    # Assume EUR for others

                    asset_dict = {
                        "name": f"Cash ({currency_name})",
                        "quantity": cash_amount,  # Store original amount as quantity
                        "purchase_price_total_eur": cash_amount_eur,  # For cash, purchase = current (no gain/loss)
                        "current_value_eur": cash_amount_eur,
                        "category": "Cash",
                    }
                    normalized_assets.append(asset_dict)

            except Exception as e:
                logger.warning(
                    f"Skipping cash row due to parsing error: {row}, error: {e}"
                )
                continue

        logger.info(
            f"Successfully normalized {len(normalized_assets)} assets (including pension and cash)"
        )
        return normalized_assets

    except Exception as e:
        logger.error(f"Failed to parse and normalize data: {e}")
        raise


def fetch_transactions_data() -> List[List[Any]]:
    """
    Fetches sell transaction data from Transactions sheet.
    
    Returns:
        list: Raw rows from Transactions sheet (excluding header)
        
    Structure from sheet:
        Row 1: ['Sell']
        Row 2: ['Date', 'Asset Name', 'Quantity', 'Purchased Price', 'Price']
        Row 3+: Data rows
    """
    try:
        service = get_sheets_service()
        cfg = config.get_config()
        
        # Get sheet ID
        spreadsheet_id = cfg.google_sheets.sheet_id
        if not spreadsheet_id:
            raise ValueError("Sheet ID not found in configuration")
        
        # Get transactions sheet name from config (default: "Transactions")
        txn_sheet_name = getattr(
            cfg.google_sheets, 
            'transactions_sheet_name', 
            'Transactions'
        )
        
        # Get transactions range from config (default: "A2:E")
        txn_range = getattr(
            cfg.google_sheets,
            'transactions_range',
            'A2:E'
        )
        
        # Construct full range name
        range_name = f"{txn_sheet_name}!{txn_range}"
        
        # Fetch data
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        
        values = result.get('values', [])
        
        # Skip header row (first row contains column names like "Date", "Asset Name", etc.)
        if values and len(values) > 0:
            # Check if first row looks like headers
            if any(header in str(values[0]) for header in ['Date', 'Asset Name', 'Quantity']):
                values = values[1:]  # Skip header
        
        logger.info(f"Fetched {len(values)} transaction rows from {txn_sheet_name} sheet")
        return values
        
    except Exception as e:
        logger.error(f"Failed to fetch transactions data: {e}")
        raise


def parse_transactions(
    raw_data: List[List[Any]], 
    gbp_to_eur: float,
    usd_to_eur: float
) -> List[Dict[str, Any]]:
    """
    Parse raw transaction data into structured transaction objects.
    
    Handles:
    - Date parsing (DD/MM/YYYY)
    - Currency detection (£, $, €)
    - EUR conversion
    - Empty/malformed row skipping
    - Future transaction filtering (based on current date)
    
    Args:
        raw_data: Raw rows [Date, Asset Name, Quantity, Purchase Price, Sell Price]
        gbp_to_eur: GBP to EUR exchange rate
        usd_to_eur: USD to EUR exchange rate
    
    Returns:
        List of transaction dicts with keys:
        - date (datetime): Transaction date (timezone-aware UTC)
        - asset_name (str): Asset name (exact case preserved)
        - quantity (float): Number of shares sold
        - sell_price_per_unit (float): Price per unit in original currency
        - currency (str): USD/GBP/EUR
        - sell_price_per_unit_eur (float): Price per unit converted to EUR
        - total_value_eur (float): Total transaction value in EUR
    """
    from datetime import datetime, timezone
    
    transactions = []
    now = datetime.now(timezone.utc)
    
    for row_num, row in enumerate(raw_data, start=3):  # Start at row 3 (data rows)
        try:
            # Skip empty rows
            if not row or len(row) < 5:
                continue
            
            # Skip rows with empty date or asset name
            if not row[0] or not row[1]:
                continue
            
            # Check if row looks like a year marker (e.g., "2026")
            date_str = str(row[0]).strip()
            if date_str.isdigit() and len(date_str) == 4:
                logger.debug(f"Row {row_num}: Skipping year marker '{date_str}'")
                continue
            
            # Parse date (DD/MM/YYYY format)
            try:
                txn_date = datetime.strptime(date_str, '%d/%m/%Y')
                # Make timezone-aware (assume UTC)
                txn_date = txn_date.replace(tzinfo=timezone.utc)
            except ValueError as e:
                logger.warning(f"Row {row_num}: Invalid date format '{date_str}', skipping - {e}")
                continue
            
            # Skip future transactions
            if txn_date > now:
                logger.info(
                    f"Row {row_num}: Skipping future transaction for {row[1]} "
                    f"dated {date_str}"
                )
                continue
            
            # Parse asset name (EXACT - preserve case)
            asset_name = str(row[1]).strip()
            
            # Parse quantity
            try:
                quantity = float(row[2]) if row[2] else 0.0
            except (ValueError, TypeError) as e:
                logger.warning(f"Row {row_num}: Invalid quantity '{row[2]}', skipping - {e}")
                continue
            
            if quantity <= 0:
                logger.warning(f"Row {row_num}: Invalid quantity {quantity} for {asset_name}, skipping")
                continue
            
            # Parse sell price (column E, index 4)
            if len(row) <= 4 or not row[4]:
                logger.warning(f"Row {row_num}: Missing sell price for {asset_name}, skipping")
                continue
            
            sell_price_str = str(row[4]).strip()
            
            # Detect currency
            currency = None
            if sell_price_str.startswith('£'):
                currency = 'GBP'
            elif sell_price_str.startswith('$'):
                currency = 'USD'
            elif sell_price_str.startswith('€'):
                currency = 'EUR'
            else:
                logger.warning(
                    f"Row {row_num}: Unknown currency in '{sell_price_str}' for {asset_name}, "
                    f"skipping"
                )
                continue
            
            # Parse numeric value (reuse existing function)
            sell_price_original = parse_currency_value(sell_price_str)
            
            if sell_price_original <= 0:
                logger.warning(
                    f"Row {row_num}: Invalid sell price {sell_price_original} for {asset_name}, "
                    f"skipping"
                )
                continue
            
            # Convert to EUR
            if currency == 'GBP':
                sell_price_eur = sell_price_original * gbp_to_eur
            elif currency == 'USD':
                sell_price_eur = sell_price_original * usd_to_eur
            else:  # EUR
                sell_price_eur = sell_price_original
            
            # Calculate total value
            total_value_eur = sell_price_eur * quantity
            
            # Create transaction object
            transaction = {
                "date": txn_date.isoformat(),
                "asset_name": asset_name,  # EXACT case preserved
                "quantity": quantity,
                "sell_price_per_unit": sell_price_original,
                "currency": currency,
                "sell_price_per_unit_eur": round(sell_price_eur, 4),
                "total_value_eur": round(total_value_eur, 2)
            }
            
            transactions.append(transaction)
            logger.debug(
                f"Row {row_num}: Parsed transaction - {asset_name}, "
                f"{quantity:.0f} shares @ {currency} {sell_price_original:.2f}"
            )
            
        except Exception as e:
            logger.warning(f"Row {row_num}: Error parsing transaction: {e}, skipping")
            continue
    
    logger.info(f"Successfully parsed {len(transactions)} transactions")
    return transactions


def fetch_buy_transactions_data() -> List[List[Any]]:
    """
    Fetches buy transaction data from Transactions sheet (columns J-M).
    
    Returns:
        list: Raw rows from Transactions sheet buy section (excluding header)
        
    Structure from sheet:
        Row 1: ['Buy']
        Row 2: ['Date', 'Asset Name', 'Quantity', 'Purchased Price']
        Row 3+: Data rows
    """
    try:
        service = get_sheets_service()
        cfg = config.get_config()
        
        # Get sheet ID
        spreadsheet_id = cfg.google_sheets.sheet_id
        if not spreadsheet_id:
            raise ValueError("Sheet ID not found in configuration")
        
        # Get transactions sheet name from config (default: "Transactions")
        txn_sheet_name = getattr(
            cfg.google_sheets, 
            'transactions_sheet_name', 
            'Transactions'
        )
        
        # Get buy transactions range from config (default: "J2:M")
        buy_txn_range = getattr(
            cfg.google_sheets,
            'buy_transactions_range',
            'J2:M'
        )
        
        # Construct full range name
        range_name = f"{txn_sheet_name}!{buy_txn_range}"
        
        # Fetch data
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        
        values = result.get('values', [])
        
        # Skip header row (first row contains column names like "Date", "Asset Name", etc.)
        if values and len(values) > 0:
            # Check if first row looks like headers
            if any(header in str(values[0]) for header in ['Date', 'Asset Name', 'Quantity']):
                values = values[1:]  # Skip header
        
        logger.info(f"Fetched {len(values)} buy transaction rows from {txn_sheet_name} sheet")
        return values
        
    except Exception as e:
        logger.error(f"Failed to fetch buy transactions data: {e}")
        raise


def parse_buy_transactions(
    raw_data: List[List[Any]], 
    gbp_to_eur: float,
    usd_to_eur: float
) -> List[Dict[str, Any]]:
    """
    Parse raw buy transaction data into structured transaction objects.
    
    Handles:
    - Date parsing (DD/MM/YYYY)
    - Currency detection (£, $, €)
    - EUR conversion
    - Empty/malformed row skipping
    - Future transaction filtering (based on current date)
    
    Args:
        raw_data: Raw rows [Date, Asset Name, Quantity, Purchase Price]
        gbp_to_eur: GBP to EUR exchange rate
        usd_to_eur: USD to EUR exchange rate
    
    Returns:
        List of transaction dicts with keys:
        - date (datetime): Transaction date (timezone-aware UTC)
        - asset_name (str): Asset name (exact case preserved)
        - quantity (float): Number of shares purchased
        - purchase_price_per_unit (float): Price per unit in original currency
        - currency (str): USD/GBP/EUR
        - purchase_price_per_unit_eur (float): Price per unit converted to EUR
        - total_value_eur (float): Total transaction value in EUR
    """
    from datetime import datetime, timezone
    
    transactions = []
    now = datetime.now(timezone.utc)
    
    for row_num, row in enumerate(raw_data, start=3):  # Start at row 3 (data rows)
        try:
            # Skip empty rows
            if not row or len(row) < 4:
                continue
            
            # Skip rows with empty date or asset name
            if not row[0] or not row[1]:
                continue
            
            # Check if row looks like a year marker (e.g., "2026")
            date_str = str(row[0]).strip()
            if date_str.isdigit() and len(date_str) == 4:
                logger.debug(f"Row {row_num}: Skipping year marker '{date_str}'")
                continue
            
            # Parse date (DD/MM/YYYY format)
            try:
                txn_date = datetime.strptime(date_str, '%d/%m/%Y')
                # Make timezone-aware (assume UTC)
                txn_date = txn_date.replace(tzinfo=timezone.utc)
            except ValueError as e:
                logger.warning(f"Row {row_num}: Invalid date format '{date_str}', skipping - {e}")
                continue
            
            # Skip future transactions
            if txn_date > now:
                logger.info(
                    f"Row {row_num}: Skipping future buy transaction for {row[1]} "
                    f"dated {date_str}"
                )
                continue
            
            # Parse asset name (EXACT - preserve case)
            asset_name = str(row[1]).strip()
            
            # Parse quantity
            try:
                quantity = float(row[2]) if row[2] else 0.0
            except (ValueError, TypeError) as e:
                logger.warning(f"Row {row_num}: Invalid quantity '{row[2]}', skipping - {e}")
                continue
            
            if quantity <= 0:
                logger.warning(f"Row {row_num}: Invalid quantity {quantity} for {asset_name}, skipping")
                continue
            
            # Parse purchase price (column M, index 3)
            if len(row) <= 3 or not row[3]:
                logger.warning(f"Row {row_num}: Missing purchase price for {asset_name}, skipping")
                continue
            
            purchase_price_str = str(row[3]).strip()
            
            # Detect currency
            currency = None
            if purchase_price_str.startswith('£'):
                currency = 'GBP'
            elif purchase_price_str.startswith('$'):
                currency = 'USD'
            elif purchase_price_str.startswith('€'):
                currency = 'EUR'
            else:
                logger.warning(
                    f"Row {row_num}: Unknown currency in '{purchase_price_str}' for {asset_name}, "
                    f"skipping"
                )
                continue
            
            # Parse numeric value (reuse existing function)
            purchase_price_original = parse_currency_value(purchase_price_str)
            
            if purchase_price_original <= 0:
                logger.warning(
                    f"Row {row_num}: Invalid purchase price {purchase_price_original} for {asset_name}, "
                    f"skipping"
                )
                continue
            
            # Convert to EUR
            if currency == 'GBP':
                purchase_price_eur = purchase_price_original * gbp_to_eur
            elif currency == 'USD':
                purchase_price_eur = purchase_price_original * usd_to_eur
            else:  # EUR
                purchase_price_eur = purchase_price_original
            
            # Calculate total value
            total_value_eur = purchase_price_eur * quantity
            
            # Create transaction object
            transaction = {
                "date": txn_date.isoformat(),
                "asset_name": asset_name,  # EXACT case preserved
                "quantity": quantity,
                "purchase_price_per_unit": purchase_price_original,
                "currency": currency,
                "purchase_price_per_unit_eur": round(purchase_price_eur, 4),
                "total_value_eur": round(total_value_eur, 2)
            }
            
            transactions.append(transaction)
            logger.debug(
                f"Row {row_num}: Parsed buy transaction - {asset_name}, "
                f"{quantity:.0f} shares @ {currency} {purchase_price_original:.2f}"
            )
            
        except Exception as e:
            logger.warning(f"Row {row_num}: Error parsing buy transaction: {e}, skipping")
            continue
    
    logger.info(f"Successfully parsed {len(transactions)} buy transactions")
    return transactions
