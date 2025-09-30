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

# Constants
ACTIVE_SHEET_NAME = "2025"

# Define the specific cell ranges for each asset category
# Column mapping: A=Name, B=Quantity, C=(Other), D=Purchase Price Total, E=Current Value Total
ASSET_RANGES = {
    "stocks_us": f"{ACTIVE_SHEET_NAME}!A4:L19",
    "stocks_eu": f"{ACTIVE_SHEET_NAME}!A20:L35",
    "bonds": f"{ACTIVE_SHEET_NAME}!A37:L39",
    "etfs": f"{ACTIVE_SHEET_NAME}!A40:L45",
}

# Define the cells containing currency conversion rates
RATES_RANGE = f"{ACTIVE_SHEET_NAME}!O2:O3"  # Assuming GBP/EUR is B2, USD/EUR is B3

# Define ranges for pension and cash data
PENSION_RANGE = f"{ACTIVE_SHEET_NAME}!A52:E53"  # Pension schemes (2nd and 3rd pillar)
CASH_RANGE = f"{ACTIVE_SHEET_NAME}!A58:B60"  # Cash positions in different currencies

logger = logging.getLogger(__name__)


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
                "security",
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

        # Load sheet details
        with open("sheet-details.json", "r") as f:
            sheet_details = json.load(f)

        spreadsheet_id = sheet_details.get("sheetId")
        if not spreadsheet_id:
            raise ValueError("Sheet ID not found in sheet-details.json")

        # Prepare batch request for all ranges
        ranges = (
            [RATES_RANGE] + list(ASSET_RANGES.values()) + [PENSION_RANGE, CASH_RANGE]
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

        # Extract asset data (ranges 1 to len(ASSET_RANGES))
        assets = {}
        for i, (category, _) in enumerate(ASSET_RANGES.items()):
            assets[category] = value_ranges[i + 1].get("values", [])

        # Extract pension data (range after asset ranges)
        pension_data = value_ranges[len(ASSET_RANGES) + 1].get("values", [])

        # Extract cash data (last range)
        cash_data = value_ranges[len(ASSET_RANGES) + 2].get("values", [])

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
