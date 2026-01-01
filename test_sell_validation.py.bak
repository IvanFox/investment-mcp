"""
Test Suite for Sell Transaction Validation

Tests the validation logic that ensures all detected sells have matching transaction records.
"""

from datetime import datetime, timezone
from agent.sell_validation import (
    detect_sells,
    find_matching_transactions,
    validate_sells_have_transactions,
    SellValidationError,
    DetectedSell,
    MissingTransaction
)


# Test Fixtures

def create_snapshot(timestamp_str, assets_list):
    """Helper to create a snapshot with given timestamp and assets."""
    return {
        "timestamp": timestamp_str,
        "total_value_eur": sum(a["current_value_eur"] for a in assets_list),
        "assets": assets_list,
        "transactions": []
    }


def create_asset(name, quantity, category="US Stocks", purchase_price=1000.0, current_value=1200.0):
    """Helper to create an asset dict."""
    return {
        "name": name,
        "quantity": quantity,
        "category": category,
        "purchase_price_total_eur": purchase_price,
        "current_value_eur": current_value
    }


def create_transaction(date_str, asset_name, quantity, sell_price_eur=10.0):
    """Helper to create a transaction dict."""
    return {
        "date": date_str,
        "asset_name": asset_name,
        "quantity": quantity,
        "sell_price_per_unit": sell_price_eur,
        "currency": "EUR",
        "sell_price_per_unit_eur": sell_price_eur,
        "total_value_eur": quantity * sell_price_eur
    }


# Test Cases

def test_no_sells_detected():
    """No quantity changes → validation passes."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    
    # Should not raise
    validate_sells_have_transactions(current, previous, [])
    print("✓ test_no_sells_detected passed")


def test_complete_sell_with_matching_transaction():
    """Position disappeared + matching transaction → validation passes."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100, purchase_price=10000, current_value=12000)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []  # Position gone
    )
    
    transactions = [
        create_transaction("2025-12-25T10:00:00Z", "Apple", 100, sell_price_eur=120.0)
    ]
    
    current["transactions"] = transactions
    
    # Should not raise
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_complete_sell_with_matching_transaction passed")


def test_complete_sell_without_transaction():
    """Position disappeared + no transaction → validation fails."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []  # Position gone
    )
    
    try:
        validate_sells_have_transactions(current, previous, [])
        assert False, "Should have raised SellValidationError"
    except SellValidationError as e:
        assert len(e.missing_transactions) == 1
        assert e.missing_transactions[0].asset_name == "Apple"
        assert e.missing_transactions[0].quantity_sold == 100.0
        print("✓ test_complete_sell_without_transaction passed")


def test_partial_sell_with_matching_transaction():
    """Quantity decreased + matching transaction → validation passes."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        [create_asset("Apple", 50)]  # Sold 50 shares
    )
    
    transactions = [
        create_transaction("2025-12-25T10:00:00Z", "Apple", 50, sell_price_eur=120.0)
    ]
    
    current["transactions"] = transactions
    
    # Should not raise
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_partial_sell_with_matching_transaction passed")


def test_partial_sell_without_transaction():
    """Quantity decreased + no transaction → validation fails."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        [create_asset("Apple", 50)]  # Sold 50 shares
    )
    
    try:
        validate_sells_have_transactions(current, previous, [])
        assert False, "Should have raised SellValidationError"
    except SellValidationError as e:
        assert len(e.missing_transactions) == 1
        assert e.missing_transactions[0].quantity_sold == 50.0
        print("✓ test_partial_sell_without_transaction passed")


def test_multiple_sells_all_have_transactions():
    """3 positions sold, 3 transactions → validation passes."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [
            create_asset("Apple", 100),
            create_asset("Microsoft", 50),
            create_asset("Google", 25)
        ]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []  # All sold
    )
    
    transactions = [
        create_transaction("2025-12-22T10:00:00Z", "Apple", 100),
        create_transaction("2025-12-23T10:00:00Z", "Microsoft", 50),
        create_transaction("2025-12-24T10:00:00Z", "Google", 25)
    ]
    
    current["transactions"] = transactions
    
    # Should not raise
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_multiple_sells_all_have_transactions passed")


def test_multiple_sells_some_missing():
    """3 positions sold, 2 transactions → validation fails, lists both missing."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [
            create_asset("Apple", 100),
            create_asset("Microsoft", 50),
            create_asset("Google", 25)
        ]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []  # All sold
    )
    
    transactions = [
        create_transaction("2025-12-22T10:00:00Z", "Apple", 100)
        # Missing Microsoft and Google
    ]
    
    current["transactions"] = transactions
    
    try:
        validate_sells_have_transactions(current, previous, transactions)
        assert False, "Should have raised SellValidationError"
    except SellValidationError as e:
        assert len(e.missing_transactions) == 2
        missing_names = [m.asset_name for m in e.missing_transactions]
        assert "Microsoft" in missing_names
        assert "Google" in missing_names
        print("✓ test_multiple_sells_some_missing passed")


def test_exact_name_matching():
    """Asset names must match exactly (case-sensitive)."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Wise", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []
    )
    
    # Transaction with different case
    transactions = [
        create_transaction("2025-12-25T10:00:00Z", "wise", 100)  # lowercase
    ]
    
    current["transactions"] = transactions
    
    try:
        validate_sells_have_transactions(current, previous, transactions)
        assert False, "Should have raised SellValidationError (case mismatch)"
    except SellValidationError as e:
        assert len(e.missing_transactions) == 1
        print("✓ test_exact_name_matching passed")


def test_quantity_tolerance():
    """±1.0 share tolerance for validation."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100.0)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []
    )
    
    # Transaction shows 99.5 shares (within 1.0 tolerance)
    transactions = [
        create_transaction("2025-12-25T10:00:00Z", "Apple", 99.5)
    ]
    
    current["transactions"] = transactions
    
    # Should pass (within tolerance)
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_quantity_tolerance passed")


def test_quantity_outside_tolerance():
    """Quantity difference ≥1.0 share should fail validation."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100.0)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []
    )
    
    # Transaction shows 98.5 shares (outside 1.0 tolerance)
    transactions = [
        create_transaction("2025-12-25T10:00:00Z", "Apple", 98.5)
    ]
    
    current["transactions"] = transactions
    
    try:
        validate_sells_have_transactions(current, previous, transactions)
        assert False, "Should have raised SellValidationError (quantity mismatch)"
    except SellValidationError as e:
        assert len(e.missing_transactions) == 1
        assert e.missing_transactions[0].quantity_in_transactions == 98.5
        print("✓ test_quantity_outside_tolerance passed")


def test_multiple_transactions_same_asset():
    """Sold 1000 shares, transactions show 500 + 500 → validation passes."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Wise", 1000)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []
    )
    
    transactions = [
        create_transaction("2025-12-22T10:00:00Z", "Wise", 500),
        create_transaction("2025-12-25T10:00:00Z", "Wise", 500)
    ]
    
    current["transactions"] = transactions
    
    # Should not raise (sum matches)
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_multiple_transactions_same_asset passed")


def test_pension_cash_excluded():
    """Pension and Cash positions should be excluded from validation."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [
            create_asset("Pension Fund", 100, category="Pension"),
            create_asset("Cash USD", 1000, category="Cash")
        ]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []  # Both gone
    )
    
    # No transactions - should pass because Pension/Cash are excluded
    validate_sells_have_transactions(current, previous, [])
    print("✓ test_pension_cash_excluded passed")


def test_fractional_quantity_ignored():
    """Quantity change < 1.0 share → no validation triggered."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100.0)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        [create_asset("Apple", 99.5)]  # Only 0.5 share change
    )
    
    # No transactions - should pass because change < 1.0 threshold
    validate_sells_have_transactions(current, previous, [])
    print("✓ test_fractional_quantity_ignored passed")


def test_date_range_filtering():
    """Only transactions within date range should be matched."""
    previous = create_snapshot(
        "2025-12-20T18:00:00Z",
        [create_asset("Apple", 100)]
    )
    current = create_snapshot(
        "2025-12-27T18:00:00Z",
        []
    )
    
    transactions = [
        # Before previous snapshot (excluded)
        create_transaction("2025-12-19T10:00:00Z", "Apple", 50),
        # Within range (included)
        create_transaction("2025-12-25T10:00:00Z", "Apple", 100),
        # After current snapshot (excluded)
        create_transaction("2025-12-28T10:00:00Z", "Apple", 50)
    ]
    
    current["transactions"] = transactions
    
    # Should pass (100 shares matched within range)
    validate_sells_have_transactions(current, previous, transactions)
    print("✓ test_date_range_filtering passed")


# Run all tests
if __name__ == "__main__":
    print("Running Sell Validation Tests...\n")
    
    test_no_sells_detected()
    test_complete_sell_with_matching_transaction()
    test_complete_sell_without_transaction()
    test_partial_sell_with_matching_transaction()
    test_partial_sell_without_transaction()
    test_multiple_sells_all_have_transactions()
    test_multiple_sells_some_missing()
    test_exact_name_matching()
    test_quantity_tolerance()
    test_quantity_outside_tolerance()
    test_multiple_transactions_same_asset()
    test_pension_cash_excluded()
    test_fractional_quantity_ignored()
    test_date_range_filtering()
    
    print("\n✅ All tests passed!")
