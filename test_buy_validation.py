"""
Test suite for buy transaction validation logic.
"""

from datetime import datetime, timezone
from agent.buy_validation import (
    detect_buys,
    find_matching_buy_transactions,
    validate_buys_have_transactions,
    BuyValidationError
)


def test_detect_buys_quantity_increase():
    """Test detection of quantity increases."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 150, "category": "Stocks"}
        ]
    }
    
    detected = detect_buys(current_snapshot, previous_snapshot, threshold=1.0)
    
    assert len(detected) == 1
    assert detected[0].asset_name == "Test Stock"
    assert detected[0].quantity_bought == 50
    assert detected[0].is_new_position == False
    print("✓ Test passed: detect_buys_quantity_increase")


def test_detect_buys_new_position():
    """Test detection of new positions."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": []
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "New Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    detected = detect_buys(current_snapshot, previous_snapshot, threshold=1.0)
    
    assert len(detected) == 1
    assert detected[0].asset_name == "New Stock"
    assert detected[0].quantity_bought == 100
    assert detected[0].is_new_position == True
    print("✓ Test passed: detect_buys_new_position")


def test_detect_buys_ignores_pension():
    """Test that pension category is excluded."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Pension Fund", "quantity": 100, "category": "Pension"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Pension Fund", "quantity": 150, "category": "Pension"}
        ]
    }
    
    detected = detect_buys(current_snapshot, previous_snapshot, threshold=1.0)
    
    assert len(detected) == 0
    print("✓ Test passed: detect_buys_ignores_pension")


def test_find_matching_buy_transactions():
    """Test transaction matching by name and date."""
    transactions = [
        {
            "asset_name": "Test Stock",
            "quantity": 30,
            "date": "2025-01-05T00:00:00Z",
            "total_value_eur": 3000
        },
        {
            "asset_name": "Test Stock",
            "quantity": 20,
            "date": "2025-01-06T00:00:00Z",
            "total_value_eur": 2000
        },
        {
            "asset_name": "Other Stock",
            "quantity": 10,
            "date": "2025-01-05T00:00:00Z",
            "total_value_eur": 1000
        }
    ]
    
    matching = find_matching_buy_transactions(
        transactions=transactions,
        asset_name="Test Stock",
        previous_date="2025-01-01T00:00:00Z",
        current_date="2025-01-08T00:00:00Z"
    )
    
    assert len(matching) == 2
    assert all(txn["asset_name"] == "Test Stock" for txn in matching)
    assert sum(txn["quantity"] for txn in matching) == 50
    print("✓ Test passed: find_matching_buy_transactions")


def test_validate_buys_exact_match():
    """Test validation passes when quantities match exactly."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 150, "category": "Stocks"}
        ],
        "buy_transactions": [
            {
                "asset_name": "Test Stock",
                "quantity": 50,
                "date": "2025-01-05T00:00:00Z",
                "total_value_eur": 5000
            }
        ]
    }
    
    buy_transactions = current_snapshot["buy_transactions"]
    
    # Should not raise exception
    validate_buys_have_transactions(
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        buy_transactions=buy_transactions
    )
    print("✓ Test passed: validate_buys_exact_match")


def test_validate_buys_missing_transaction():
    """Test validation fails when transaction is missing."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 150, "category": "Stocks"}
        ],
        "buy_transactions": []
    }
    
    try:
        validate_buys_have_transactions(
            current_snapshot=current_snapshot,
            previous_snapshot=previous_snapshot,
            buy_transactions=[]
        )
        assert False, "Should have raised BuyValidationError"
    except BuyValidationError as e:
        assert "Test Stock" in str(e)
        assert "Missing buy transaction records" in str(e)
        print("✓ Test passed: validate_buys_missing_transaction")


def test_validate_buys_new_position_missing():
    """Test validation fails for new position without transaction."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": []
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "New Stock", "quantity": 100, "category": "Stocks"}
        ],
        "buy_transactions": []
    }
    
    try:
        validate_buys_have_transactions(
            current_snapshot=current_snapshot,
            previous_snapshot=previous_snapshot,
            buy_transactions=[]
        )
        assert False, "Should have raised BuyValidationError"
    except BuyValidationError as e:
        assert "New Stock" in str(e)
        assert "NEW POSITION" in str(e)
        print("✓ Test passed: validate_buys_new_position_missing")


def test_validate_buys_partial_match():
    """Test validation fails when only partial quantity is in transactions."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 150, "category": "Stocks"}
        ],
        "buy_transactions": [
            {
                "asset_name": "Test Stock",
                "quantity": 30,  # Only 30 of 50
                "date": "2025-01-05T00:00:00Z",
                "total_value_eur": 3000
            }
        ]
    }
    
    buy_transactions = current_snapshot["buy_transactions"]
    
    try:
        validate_buys_have_transactions(
            current_snapshot=current_snapshot,
            previous_snapshot=previous_snapshot,
            buy_transactions=buy_transactions
        )
        assert False, "Should have raised BuyValidationError"
    except BuyValidationError as e:
        assert "Test Stock" in str(e)
        assert "PARTIAL" in str(e)
        assert "Missing: 20" in str(e)
        print("✓ Test passed: validate_buys_partial_match")


def test_validate_buys_multiple_transactions():
    """Test validation passes when multiple transactions sum correctly."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 180, "category": "Stocks"}
        ],
        "buy_transactions": [
            {
                "asset_name": "Test Stock",
                "quantity": 50,
                "date": "2025-01-03T00:00:00Z",
                "total_value_eur": 5000
            },
            {
                "asset_name": "Test Stock",
                "quantity": 30,
                "date": "2025-01-05T00:00:00Z",
                "total_value_eur": 3000
            }
        ]
    }
    
    buy_transactions = current_snapshot["buy_transactions"]
    
    # Should not raise exception (50 + 30 = 80)
    validate_buys_have_transactions(
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        buy_transactions=buy_transactions
    )
    print("✓ Test passed: validate_buys_multiple_transactions")


def test_validate_buys_no_buys_detected():
    """Test validation passes when no buys detected."""
    previous_snapshot = {
        "timestamp": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ]
    }
    
    current_snapshot = {
        "timestamp": "2025-01-08T00:00:00Z",
        "assets": [
            {"name": "Test Stock", "quantity": 100, "category": "Stocks"}
        ],
        "buy_transactions": []
    }
    
    # Should not raise exception
    validate_buys_have_transactions(
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        buy_transactions=[]
    )
    print("✓ Test passed: validate_buys_no_buys_detected")


if __name__ == "__main__":
    print("Running buy validation tests...\n")
    
    test_detect_buys_quantity_increase()
    test_detect_buys_new_position()
    test_detect_buys_ignores_pension()
    test_find_matching_buy_transactions()
    test_validate_buys_exact_match()
    test_validate_buys_missing_transaction()
    test_validate_buys_new_position_missing()
    test_validate_buys_partial_match()
    test_validate_buys_multiple_transactions()
    test_validate_buys_no_buys_detected()
    
    print("\n✅ All tests passed!")
