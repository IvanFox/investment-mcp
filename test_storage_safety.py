#!/usr/bin/env python3
"""
Test script for storage.py data protection features.

Tests the following safety mechanisms:
1. Fail-fast on corrupted JSON (preserve file)
2. Automatic backup creation (.bak file)
3. Atomic writes (temp file + rename)
4. Input validation (reject invalid snapshot structure)
5. Proper error handling and logging
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import storage


# Test data
VALID_SNAPSHOT = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "total_value_eur": 10000.50,
    "assets": [
        {
            "name": "Test Stock",
            "quantity": 100,
            "purchase_price_total_eur": 5000.0,
            "current_value_eur": 5500.0,
            "category": "US Stocks",
        }
    ],
}

INVALID_SNAPSHOT_MISSING_FIELD = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "assets": [],
}

INVALID_SNAPSHOT_WRONG_TYPE = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "total_value_eur": "not a number",
    "assets": [],
}


def cleanup_test_files():
    """Remove test files before and after tests."""
    for file in [storage.HISTORY_FILE, storage.BACKUP_FILE, storage.TEMP_FILE]:
        if os.path.exists(file):
            os.remove(file)
            print(f"✓ Cleaned up {file}")


def test_1_valid_snapshot_first_run():
    """Test 1: Save valid snapshot when no history exists."""
    print("\n" + "=" * 70)
    print("TEST 1: Valid snapshot - first run (no existing file)")
    print("=" * 70)

    cleanup_test_files()

    try:
        storage.save_snapshot(VALID_SNAPSHOT)

        # Verify file was created
        assert os.path.exists(storage.HISTORY_FILE), "History file not created"

        # Verify content
        with open(storage.HISTORY_FILE, "r") as f:
            history = json.load(f)

        assert isinstance(history, list), "History is not a list"
        assert len(history) == 1, f"Expected 1 snapshot, got {len(history)}"
        assert history[0]["total_value_eur"] == VALID_SNAPSHOT["total_value_eur"]

        # Backup should NOT exist on first run
        assert not os.path.exists(storage.BACKUP_FILE), (
            "Backup file should not exist on first run"
        )

        print("✅ PASSED: Valid snapshot saved successfully")
        print(f"   - History file created: {storage.HISTORY_FILE}")
        print(f"   - Snapshots saved: 1")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_2_valid_snapshot_append():
    """Test 2: Append valid snapshot to existing history."""
    print("\n" + "=" * 70)
    print("TEST 2: Valid snapshot - append to existing history")
    print("=" * 70)

    try:
        # Create second snapshot
        snapshot2 = VALID_SNAPSHOT.copy()
        snapshot2["total_value_eur"] = 11000.75

        storage.save_snapshot(snapshot2)

        # Verify backup was created
        assert os.path.exists(storage.BACKUP_FILE), "Backup file not created"

        # Verify content
        with open(storage.HISTORY_FILE, "r") as f:
            history = json.load(f)

        assert len(history) == 2, f"Expected 2 snapshots, got {len(history)}"
        assert history[1]["total_value_eur"] == 11000.75

        # Verify backup contains old version (1 snapshot)
        with open(storage.BACKUP_FILE, "r") as f:
            backup = json.load(f)

        assert len(backup) == 1, f"Backup should have 1 snapshot, got {len(backup)}"

        print("✅ PASSED: Snapshot appended successfully")
        print(f"   - Total snapshots: 2")
        print(f"   - Backup created: {storage.BACKUP_FILE}")
        print(f"   - Backup contains previous version (1 snapshot)")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_3_corrupted_json_fails():
    """Test 3: Corrupted JSON causes fail-fast (file preserved)."""
    print("\n" + "=" * 70)
    print("TEST 3: Corrupted JSON - fail-fast protection")
    print("=" * 70)

    # Create corrupted JSON file
    corrupted_content = '{"invalid": json content without closing brace'
    with open(storage.HISTORY_FILE, "w") as f:
        f.write(corrupted_content)

    print(f"   Created corrupted file with content: {corrupted_content[:50]}...")

    try:
        storage.save_snapshot(VALID_SNAPSHOT)
        print("❌ FAILED: Should have raised JSONDecodeError")
        return False

    except json.JSONDecodeError as e:
        # Verify the corrupted file was preserved
        with open(storage.HISTORY_FILE, "r") as f:
            preserved_content = f.read()

        assert preserved_content == corrupted_content, "Corrupted file was modified!"

        print("✅ PASSED: Corrupted JSON detected and file preserved")
        print(f"   - Exception raised: JSONDecodeError")
        print(f"   - Error message: {str(e)[:100]}...")
        print(f"   - Original file preserved unchanged")
        return True

    except Exception as e:
        print(f"❌ FAILED: Wrong exception type: {type(e).__name__}")
        print(f"   Error: {e}")
        return False


def test_4_invalid_snapshot_structure():
    """Test 4: Invalid snapshot structure rejected."""
    print("\n" + "=" * 70)
    print("TEST 4: Invalid snapshot structure - validation")
    print("=" * 70)

    cleanup_test_files()

    # Test 4a: Missing required field
    print("\n   Test 4a: Missing required field (total_value_eur)")
    try:
        storage.save_snapshot(INVALID_SNAPSHOT_MISSING_FIELD)
        print("   ❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        assert "missing required field" in str(e).lower()
        print(f"   ✅ PASSED: Rejected with ValueError: {e}")
    except Exception as e:
        print(f"   ❌ FAILED: Wrong exception: {type(e).__name__}: {e}")
        return False

    # Test 4b: Wrong field type
    print("\n   Test 4b: Wrong field type (total_value_eur is string)")
    try:
        storage.save_snapshot(INVALID_SNAPSHOT_WRONG_TYPE)
        print("   ❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        assert "must be a number" in str(e).lower()
        print(f"   ✅ PASSED: Rejected with ValueError: {e}")
    except Exception as e:
        print(f"   ❌ FAILED: Wrong exception: {type(e).__name__}: {e}")
        return False

    # Verify no files were created
    assert not os.path.exists(storage.HISTORY_FILE), (
        "History file should not exist after validation failure"
    )
    print("\n✅ PASSED: All invalid structures rejected, no files created")
    return True


def test_5_atomic_write_integrity():
    """Test 5: Verify atomic write doesn't leave temp files."""
    print("\n" + "=" * 70)
    print("TEST 5: Atomic write - no temp file remnants")
    print("=" * 70)

    cleanup_test_files()

    try:
        storage.save_snapshot(VALID_SNAPSHOT)

        # Verify temp file doesn't exist after successful write
        assert not os.path.exists(storage.TEMP_FILE), "Temp file should be cleaned up"

        # Verify history file exists and is valid
        assert os.path.exists(storage.HISTORY_FILE), "History file not created"

        with open(storage.HISTORY_FILE, "r") as f:
            history = json.load(f)

        assert len(history) == 1

        print("✅ PASSED: Atomic write successful")
        print(f"   - No temp file remnants")
        print(f"   - History file valid and complete")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_6_backup_recovery():
    """Test 6: Backup file can be used for recovery."""
    print("\n" + "=" * 70)
    print("TEST 6: Backup recovery scenario")
    print("=" * 70)

    cleanup_test_files()

    try:
        # Create initial snapshot
        storage.save_snapshot(VALID_SNAPSHOT)

        # Create second snapshot (triggers backup)
        snapshot2 = VALID_SNAPSHOT.copy()
        snapshot2["total_value_eur"] = 20000.0
        storage.save_snapshot(snapshot2)

        # Verify we have 2 snapshots
        with open(storage.HISTORY_FILE, "r") as f:
            current = json.load(f)
        assert len(current) == 2, f"Expected 2 snapshots, got {len(current)}"

        # Verify backup has 1 snapshot (previous version)
        with open(storage.BACKUP_FILE, "r") as f:
            backup = json.load(f)
        assert len(backup) == 1, f"Backup should have 1 snapshot, got {len(backup)}"

        # Simulate recovery: restore backup
        print("   Simulating recovery from backup...")
        shutil.copy2(storage.BACKUP_FILE, storage.HISTORY_FILE)

        # Verify restored version
        with open(storage.HISTORY_FILE, "r") as f:
            restored = json.load(f)

        assert len(restored) == 1, (
            f"Restored should have 1 snapshot, got {len(restored)}"
        )
        assert restored[0]["total_value_eur"] == VALID_SNAPSHOT["total_value_eur"]

        print("✅ PASSED: Backup recovery successful")
        print(f"   - Backup file restored successfully")
        print(f"   - Previous version recovered (1 snapshot)")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("STORAGE SAFETY TEST SUITE")
    print("=" * 70)
    print(f"Testing file: {os.path.abspath(storage.HISTORY_FILE)}")
    print(f"Testing backup: {os.path.abspath(storage.BACKUP_FILE)}")

    tests = [
        test_1_valid_snapshot_first_run,
        test_2_valid_snapshot_append,
        test_3_corrupted_json_fails,
        test_4_invalid_snapshot_structure,
        test_5_atomic_write_integrity,
        test_6_backup_recovery,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Storage safety mechanisms working correctly.")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")

    # Cleanup
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)
    cleanup_test_files()
    print("\n✓ All test files cleaned up")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
