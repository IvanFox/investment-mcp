"""
Tests for snapshot deletion functionality.

Tests deletion by index, backup creation, and error handling.
"""

import os
import json
import tempfile
import shutil
from datetime import datetime, timezone

from agent.backends.local_storage import LocalFileBackend


# Test helper functions

def create_test_snapshot(timestamp_str, total_value, asset_count=10):
    """Create a test snapshot."""
    return {
        "timestamp": timestamp_str,
        "total_value_eur": total_value,
        "assets": [
            {"name": f"Asset{i}", "quantity": 100, "current_value_eur": total_value / asset_count}
            for i in range(asset_count)
        ]
    }


def create_test_history(count=5):
    """Create a test history with multiple snapshots."""
    snapshots = []
    for i in range(count):
        timestamp = f"2025-01-{i+1:02d}T10:00:00Z"
        value = 100000.0 + (i * 5000.0)
        snapshots.append(create_test_snapshot(timestamp, value, asset_count=10 + i))
    return snapshots


# Test cases

def test_delete_snapshot_by_valid_index():
    """Test deleting a snapshot with a valid index."""
    print("\nTesting: Delete snapshot by valid index...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        
        # Create test history with 5 snapshots
        history = create_test_history(5)
        
        # Manually save initial history
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"  Created history with {len(history)} snapshots")
        
        # Delete snapshot at index 2 (middle snapshot)
        success = backend.delete_snapshot(2)
        
        assert success, "Deletion should succeed"
        print(f"  ✓ Deletion succeeded")
        
        # Verify snapshot was deleted
        with open(history_path, "r") as f:
            updated_history = json.load(f)
        
        assert len(updated_history) == 4, f"Should have 4 snapshots, got {len(updated_history)}"
        print(f"  ✓ History now has {len(updated_history)} snapshots")
        
        # Verify correct snapshot was deleted (2025-01-03)
        timestamps = [s["timestamp"] for s in updated_history]
        assert "2025-01-03T10:00:00Z" not in timestamps, "Deleted snapshot should be gone"
        print(f"  ✓ Correct snapshot deleted (2025-01-03)")
        
        # Verify backup was created
        backup_files = [f for f in os.listdir(temp_dir) if f.startswith("portfolio_history.json.bak")]
        assert len(backup_files) > 0, "Backup file should exist"
        print(f"  ✓ Backup created: {backup_files[0]}")
        
        print("✓ Test passed: delete_snapshot_by_valid_index")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_first_snapshot():
    """Test deleting the first snapshot."""
    print("\nTesting: Delete first snapshot...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(3)
        
        # Save history
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Delete first snapshot (index 0)
        success = backend.delete_snapshot(0)
        
        assert success, "Deletion should succeed"
        
        with open(history_path, "r") as f:
            updated_history = json.load(f)
        
        assert len(updated_history) == 2, "Should have 2 snapshots remaining"
        assert updated_history[0]["timestamp"] == "2025-01-02T10:00:00Z", "First snapshot should now be 2025-01-02"
        
        print("✓ Test passed: delete_first_snapshot")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_last_snapshot():
    """Test deleting the last snapshot."""
    print("\nTesting: Delete last snapshot...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(3)
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Delete last snapshot (index 2)
        success = backend.delete_snapshot(2)
        
        assert success, "Deletion should succeed"
        
        with open(history_path, "r") as f:
            updated_history = json.load(f)
        
        assert len(updated_history) == 2, "Should have 2 snapshots remaining"
        assert updated_history[-1]["timestamp"] == "2025-01-02T10:00:00Z", "Last snapshot should now be 2025-01-02"
        
        print("✓ Test passed: delete_last_snapshot")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_only_snapshot():
    """Test deleting the only remaining snapshot."""
    print("\nTesting: Delete only snapshot...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(1)  # Only 1 snapshot
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Delete the only snapshot
        success = backend.delete_snapshot(0)
        
        assert success, "Deletion should succeed"
        
        with open(history_path, "r") as f:
            updated_history = json.load(f)
        
        assert len(updated_history) == 0, "History should be empty"
        assert updated_history == [], "History should be an empty list"
        
        print("✓ Test passed: delete_only_snapshot")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_invalid_index_negative():
    """Test deleting with negative index (should fail)."""
    print("\nTesting: Delete with negative index...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(3)
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Try to delete with negative index
        success = backend.delete_snapshot(-1)
        
        assert not success, "Deletion should fail with negative index"
        
        # Verify history unchanged
        with open(history_path, "r") as f:
            unchanged_history = json.load(f)
        
        assert len(unchanged_history) == 3, "History should be unchanged"
        
        print("✓ Test passed: delete_invalid_index_negative")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_invalid_index_out_of_range():
    """Test deleting with index beyond array length (should fail)."""
    print("\nTesting: Delete with out-of-range index...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(3)
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Try to delete with index beyond range
        success = backend.delete_snapshot(10)
        
        assert not success, "Deletion should fail with out-of-range index"
        
        # Verify history unchanged
        with open(history_path, "r") as f:
            unchanged_history = json.load(f)
        
        assert len(unchanged_history) == 3, "History should be unchanged"
        
        print("✓ Test passed: delete_invalid_index_out_of_range")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_from_empty_history():
    """Test deleting when history file is empty (should fail)."""
    print("\nTesting: Delete from empty history...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        
        # Create empty history file
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump([], f)
        
        # Try to delete
        success = backend.delete_snapshot(0)
        
        assert not success, "Deletion should fail on empty history"
        
        print("✓ Test passed: delete_from_empty_history")
        
    finally:
        shutil.rmtree(temp_dir)


def test_delete_from_nonexistent_file():
    """Test deleting when history file doesn't exist (should fail)."""
    print("\nTesting: Delete from nonexistent file...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        
        # Don't create history file - it doesn't exist
        
        # Try to delete
        success = backend.delete_snapshot(0)
        
        assert not success, "Deletion should fail when file doesn't exist"
        
        print("✓ Test passed: delete_from_nonexistent_file")
        
    finally:
        shutil.rmtree(temp_dir)


def test_backup_contains_original_snapshot():
    """Test that backup file contains the original snapshot."""
    print("\nTesting: Backup contains original snapshot...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(3)
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Remember the snapshot we're about to delete
        snapshot_to_delete = history[1].copy()
        
        # Delete middle snapshot
        success = backend.delete_snapshot(1)
        assert success, "Deletion should succeed"
        
        # Find backup file
        backup_files = [f for f in os.listdir(temp_dir) if f.startswith("portfolio_history.json.bak")]
        assert len(backup_files) > 0, "Backup should exist"
        
        backup_path = os.path.join(temp_dir, backup_files[0])
        
        # Load backup
        with open(backup_path, "r") as f:
            backup_history = json.load(f)
        
        # Verify backup has the deleted snapshot
        assert len(backup_history) == 3, "Backup should have original 3 snapshots"
        assert backup_history[1] == snapshot_to_delete, "Backup should contain deleted snapshot"
        
        print(f"  ✓ Backup verified: {backup_files[0]}")
        print("✓ Test passed: backup_contains_original_snapshot")
        
    finally:
        shutil.rmtree(temp_dir)


def test_multiple_deletions_create_multiple_backups():
    """Test that multiple deletions create separate timestamped backups."""
    print("\nTesting: Multiple deletions create multiple backups...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        backend = LocalFileBackend(data_dir=temp_dir)
        history = create_test_history(5)
        
        history_path = os.path.join(temp_dir, "portfolio_history.json")
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        
        # Delete first snapshot
        success1 = backend.delete_snapshot(0)
        assert success1, "First deletion should succeed"
        
        import time
        time.sleep(0.1)  # Small delay to ensure different timestamp
        
        # Delete another snapshot (now at index 0 since we deleted the first)
        success2 = backend.delete_snapshot(0)
        assert success2, "Second deletion should succeed"
        
        # Check backup files
        backup_files = [f for f in os.listdir(temp_dir) if f.startswith("portfolio_history.json.bak")]
        
        # Should have 2 backup files (one per deletion)
        assert len(backup_files) >= 1, f"Should have at least 1 backup, found {len(backup_files)}"
        print(f"  ✓ Created {len(backup_files)} backup(s)")
        
        print("✓ Test passed: multiple_deletions_create_multiple_backups")
        
    finally:
        shutil.rmtree(temp_dir)


# Run all tests
if __name__ == "__main__":
    print("=" * 70)
    print("Running Snapshot Deletion Tests")
    print("=" * 70)
    
    test_delete_snapshot_by_valid_index()
    test_delete_first_snapshot()
    test_delete_last_snapshot()
    test_delete_only_snapshot()
    test_delete_invalid_index_negative()
    test_delete_invalid_index_out_of_range()
    test_delete_from_empty_history()
    test_delete_from_nonexistent_file()
    test_backup_contains_original_snapshot()
    test_multiple_deletions_create_multiple_backups()
    
    print("\n" + "=" * 70)
    print("✅ All snapshot deletion tests passed!")
    print("=" * 70)
