"""
Tests for transaction storage module.

Tests change detection, hash computation, and storage operations.
"""

import os
import json
import tempfile
import shutil
from datetime import datetime, timezone

# Import transaction_storage module directly
import agent.transaction_storage as transaction_storage
from agent.backends.local_storage import LocalFileBackend


# Test helper functions

def create_sell_transaction(asset_name, quantity, price_eur):
    """Create a test sell transaction."""
    return {
        "date": "2025-01-15T00:00:00+00:00",
        "asset_name": asset_name,
        "quantity": quantity,
        "sell_price_per_unit": price_eur / 1.16,  # Approximate original price
        "currency": "GBP",
        "sell_price_per_unit_eur": price_eur,
        "total_value_eur": price_eur * quantity
    }


def create_buy_transaction(asset_name, quantity, price_eur):
    """Create a test buy transaction."""
    return {
        "date": "2025-01-20T00:00:00+00:00",
        "asset_name": asset_name,
        "quantity": quantity,
        "purchase_price_per_unit": price_eur / 1.16,  # Approximate original price
        "currency": "GBP",
        "purchase_price_per_unit_eur": price_eur,
        "total_value_eur": price_eur * quantity
    }


# Test cases

def test_compute_transaction_hash_consistency():
    """Hash should be same for same transactions in different order."""
    print("\nTesting: Hash consistency for reordered transactions...")
    
    txns_a = [
        create_sell_transaction("Apple", 100, 120.0),
        create_sell_transaction("Google", 50, 150.0)
    ]
    
    txns_b = [
        create_sell_transaction("Google", 50, 150.0),
        create_sell_transaction("Apple", 100, 120.0)
    ]
    
    hash_a = transaction_storage.compute_transaction_hash(txns_a)
    hash_b = transaction_storage.compute_transaction_hash(txns_b)
    
    assert hash_a == hash_b, f"Hashes should match for reordered transactions: {hash_a} != {hash_b}"
    print(f"✓ Hash consistency verified: {hash_a}")


def test_compute_transaction_hash_sensitivity():
    """Hash should change if any transaction data changes."""
    print("\nTesting: Hash sensitivity to data changes...")
    
    txns_original = [
        create_sell_transaction("Apple", 100, 120.0)
    ]
    
    # Change quantity
    txns_modified = [
        create_sell_transaction("Apple", 101, 120.0)
    ]
    
    hash_original = transaction_storage.compute_transaction_hash(txns_original)
    hash_modified = transaction_storage.compute_transaction_hash(txns_modified)
    
    assert hash_original != hash_modified, "Hash should change when quantity changes"
    print(f"✓ Hash changed as expected: {hash_original[:16]}... -> {hash_modified[:16]}...")


def test_compute_transaction_hash_empty():
    """Hash of empty list should be deterministic."""
    print("\nTesting: Hash of empty transaction list...")
    
    hash1 = transaction_storage.compute_transaction_hash([])
    hash2 = transaction_storage.compute_transaction_hash([])
    
    assert hash1 == hash2, "Empty list hash should be consistent"
    assert hash1.startswith("sha256:"), "Hash should have sha256: prefix"
    print(f"✓ Empty list hash: {hash1}")


def test_save_and_get_transactions():
    """Test saving and retrieving transactions."""
    print("\nTesting: Save and get transactions...")
    
    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize test backend
        backend = LocalFileBackend(data_dir=temp_dir)
        
        # Create test data
        sell_txns = [create_sell_transaction("Apple", 100, 120.0)]
        buy_txns = [create_buy_transaction("Google", 50, 150.0)]
        rates = {"gbp_to_eur": 1.16, "usd_to_eur": 0.85}
        
        # Build transaction data manually (simulating what save_transactions does)
        sell_hash = transaction_storage.compute_transaction_hash(sell_txns)
        buy_hash = transaction_storage.compute_transaction_hash(buy_txns)
        
        txn_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "sell_transactions": sell_txns,
            "buy_transactions": buy_txns,
            "metadata": {
                "sell_count": len(sell_txns),
                "buy_count": len(buy_txns),
                "sell_hash": sell_hash,
                "buy_hash": buy_hash,
                "source_sheet": "Transactions",
                "currency_rates": rates
            }
        }
        
        # Save
        success = backend.save_transactions(txn_data)
        assert success, "Save should succeed"
        
        # Retrieve
        loaded_data = backend.get_transactions()
        assert loaded_data is not None, "Should retrieve saved data"
        assert len(loaded_data["sell_transactions"]) == 1, "Should have 1 sell transaction"
        assert len(loaded_data["buy_transactions"]) == 1, "Should have 1 buy transaction"
        assert loaded_data["metadata"]["sell_hash"] == sell_hash, "Sell hash should match"
        assert loaded_data["metadata"]["buy_hash"] == buy_hash, "Buy hash should match"
        
        print(f"✓ Save and retrieval successful")
        print(f"  Sells: {len(loaded_data['sell_transactions'])}")
        print(f"  Buys: {len(loaded_data['buy_transactions'])}")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_get_transactions_nonexistent():
    """Get should return None if no file exists."""
    print("\nTesting: Get transactions from nonexistent file...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        data = backend.get_transactions()
        
        assert data is None, "Should return None for nonexistent file"
        print("✓ Correctly returned None for nonexistent file")
        
    finally:
        shutil.rmtree(temp_dir)


def test_hash_stability_across_rounding():
    """Minor float rounding should not change hash (normalized to 4 decimals)."""
    print("\nTesting: Hash stability with float rounding...")
    
    # Create transactions with slight float differences
    txn1 = create_sell_transaction("Apple", 100, 120.1234)
    txn2 = create_sell_transaction("Apple", 100, 120.12340001)  # Tiny difference
    
    hash1 = transaction_storage.compute_transaction_hash([txn1])
    hash2 = transaction_storage.compute_transaction_hash([txn2])
    
    # Note: Due to normalization to 4 decimals, hashes should be same
    # However, 120.1234 vs 120.12340001 will both round to 120.1234
    print(f"  Hash 1: {hash1[:32]}...")
    print(f"  Hash 2: {hash2[:32]}...")
    
    # They should be the same due to rounding to 4 decimals
    assert hash1 == hash2, "Hash should be stable with minor float differences"
    print("✓ Hash stable across minor float differences")


def test_transaction_structure_validation():
    """Invalid transaction structure should be detected."""
    print("\nTesting: Transaction structure validation...")
    
    # Invalid: missing required field
    invalid_data = {
        "last_updated": "2025-01-01T00:00:00Z",
        "sell_transactions": [],
        # Missing buy_transactions and metadata
    }
    
    try:
        transaction_storage._validate_transaction_structure(invalid_data)
        assert False, "Should have raised ValueError for invalid structure"
    except ValueError as e:
        assert "missing required field" in str(e).lower()
        print(f"✓ Validation correctly rejected invalid structure: {e}")


# Run all tests
if __name__ == "__main__":
    print("=" * 70)
    print("Running Transaction Storage Tests")
    print("=" * 70)
    
    test_compute_transaction_hash_consistency()
    test_compute_transaction_hash_sensitivity()
    test_compute_transaction_hash_empty()
    test_save_and_get_transactions()
    test_get_transactions_nonexistent()
    test_hash_stability_across_rounding()
    test_transaction_structure_validation()
    
    print("\n" + "=" * 70)
    print("✅ All transaction storage tests passed!")
    print("=" * 70)
