#!/usr/bin/env python3
"""
Test suite for GCP storage backend.

SETUP REQUIRED:
1. Create test bucket (one-time setup):
   gsutil mb -l europe-north1 gs://investment_snapshots_test
   
   Or with custom region:
   export INVESTMENT_TEST_REGION=us-central1
   gsutil mb -l $INVESTMENT_TEST_REGION gs://investment_snapshots_test

2. Ensure GCP credentials are in Keychain (uses same creds as production)

3. (Optional) Override test bucket name:
   export INVESTMENT_TEST_BUCKET=my-custom-test-bucket

NOTE: 
- These are integration tests that require internet connectivity
- Tests write temporary data to test bucket
- All test data is automatically cleaned up after execution
- Production bucket (investment_snapshots) is NEVER touched

Run with: uv run python test_gcp_storage.py
"""

import json
import logging
import os
import shutil
from datetime import datetime

from agent.backends.gcp_storage import GCPStorageBackend
from agent.backends.local_storage import LocalFileBackend
from agent.backends.hybrid_storage import HybridStorageBackend
import subprocess

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test bucket configuration
# Override via environment variables:
#   INVESTMENT_TEST_BUCKET - Custom test bucket name
#   INVESTMENT_TEST_REGION - Custom region for bucket creation
TEST_BUCKET_NAME = os.environ.get('INVESTMENT_TEST_BUCKET', 'investment_snapshots_test')
TEST_BUCKET_REGION = os.environ.get('INVESTMENT_TEST_REGION', 'europe-north1')

# Force test mode for this test suite - override config to use test bucket
os.environ['INVESTMENT_GCP_BUCKET'] = TEST_BUCKET_NAME

TEST_SNAPSHOT = {
    "timestamp": datetime.now().isoformat(),
    "total_value_eur": 100000.0,
    "assets": [
        {
            "name": "Test Asset",
            "category": "Test",
            "quantity": 10,
            "current_value_eur": 1000.0
        }
    ]
}


def load_test_credentials():
    """Load credentials from Keychain for testing."""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "mcp-portfolio-agent", 
         "-s", "google-sheets-credentials", "-w"],
        capture_output=True,
        text=True,
        check=True
    )
    hex_data = result.stdout.strip()
    json_bytes = bytes.fromhex(hex_data)
    return json.loads(json_bytes.decode('utf-8'))


def cleanup_test_bucket():
    """
    Clean up all test data from test bucket after test execution.
    
    This ensures test data doesn't pollute the test bucket between runs.
    Uses the delete_all_snapshots() method which deletes the entire
    portfolio_history.json file from the bucket.
    """
    print("\n" + "="*60)
    print("CLEANUP: Deleting test data from test bucket")
    print("="*60)
    
    try:
        creds = load_test_credentials()
        backend = GCPStorageBackend(TEST_BUCKET_NAME, creds)
        
        if backend.is_available():
            success = backend.delete_all_snapshots()
            if success:
                print(f"✅ Test data deleted from gs://{TEST_BUCKET_NAME}")
            else:
                print(f"⚠️  Failed to delete test data (non-critical)")
        else:
            print("⚠️  Test bucket not available, skipping cleanup")
    except Exception as e:
        print(f"⚠️  Cleanup failed (non-critical): {e}")
        import traceback
        traceback.print_exc()


def test_gcp_backend():
    """Test GCP backend directly."""
    print("\n" + "="*60)
    print("TEST 1: GCP Backend Direct Access")
    print("="*60)
    
    creds = load_test_credentials()
    backend = GCPStorageBackend(TEST_BUCKET_NAME, creds)
    
    # Test availability
    print("Checking GCP availability...")
    assert backend.is_available(), "GCP backend should be available"
    print("✅ GCP backend is available")
    
    # Get current state
    print("\nChecking existing data...")
    initial_snapshots = backend.get_all_snapshots()
    print(f"✅ Found {len(initial_snapshots)} existing snapshots in GCS")
    
    # Test save
    print("\nSaving test snapshot...")
    success = backend.save_snapshot(TEST_SNAPSHOT)
    assert success, "Save should succeed"
    print("✅ Snapshot saved to GCP")
    
    # Test retrieve
    print("\nRetrieving latest snapshot...")
    latest = backend.get_latest_snapshot()
    assert latest is not None, "Should retrieve latest snapshot"
    assert latest["total_value_eur"] == 100000.0, "Data should match"
    print("✅ Snapshot retrieved from GCP correctly")
    
    # Verify count increased
    print("\nVerifying snapshot count...")
    final_snapshots = backend.get_all_snapshots()
    assert len(final_snapshots) == len(initial_snapshots) + 1, "Should have one more snapshot"
    print(f"✅ Snapshot count correct: {len(final_snapshots)} total")
    
    print("\n✅ All GCP backend tests passed!")
    return True


def test_hybrid_backend():
    """Test hybrid backend with fallback."""
    print("\n" + "="*60)
    print("TEST 2: Hybrid Backend with Dual-Write")
    print("="*60)
    
    # Create test directory for local backend
    test_dir = "./test_data_hybrid"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    try:
        creds = load_test_credentials()
        gcp_backend = GCPStorageBackend(TEST_BUCKET_NAME, creds)
        local_backend = LocalFileBackend(data_dir=test_dir)
        
        hybrid = HybridStorageBackend(gcp_backend, local_backend)
        
        # Test dual-write
        print("Testing dual-write to both backends...")
        test_snapshot_2 = TEST_SNAPSHOT.copy()
        test_snapshot_2["timestamp"] = datetime.now().isoformat()
        test_snapshot_2["total_value_eur"] = 200000.0
        
        success = hybrid.save_snapshot(test_snapshot_2)
        assert success, "Hybrid save should succeed"
        print("✅ Snapshot saved to hybrid backend")
        
        # Check sync status
        print("\nChecking sync status...")
        status = hybrid.get_sync_status()
        print(f"   Primary (GCP) available: {status['primary_available']}")
        print(f"   Fallback (local) available: {status['fallback_available']}")
        print(f"   Pending syncs: {status['pending_syncs']}")
        print(f"   Fully synced: {status['fully_synced']}")
        
        assert status['primary_available'], "Primary should be available"
        assert status['fallback_available'], "Fallback should be available"
        assert status['fully_synced'], "Should be fully synced"
        print("✅ Sync status correct")
        
        # Verify both backends have the data
        print("\nVerifying data in both backends...")
        gcp_latest = gcp_backend.get_latest_snapshot()
        local_latest = local_backend.get_latest_snapshot()
        
        assert gcp_latest is not None, "GCP should have snapshot"
        assert local_latest is not None, "Local should have snapshot"
        assert gcp_latest["total_value_eur"] == 200000.0, "GCP data should match"
        assert local_latest["total_value_eur"] == 200000.0, "Local data should match"
        print("✅ Data verified in both GCP and local storage")
        
        # Test retrieve (should use primary)
        print("\nRetrieving via hybrid backend...")
        latest = hybrid.get_latest_snapshot()
        assert latest is not None
        assert latest["total_value_eur"] == 200000.0
        print("✅ Retrieved correct snapshot via hybrid backend")
        
        print("\n✅ All hybrid backend tests passed!")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_fallback_scenario():
    """Test fallback when GCP is unavailable."""
    print("\n" + "="*60)
    print("TEST 3: Fallback Behavior (Simulated GCP Outage)")
    print("="*60)
    
    # Create test directory
    test_dir = "./test_data_fallback"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    try:
        # Create a mock GCP backend that's always unavailable
        class MockUnavailableBackend:
            def is_available(self):
                return False
            def save_snapshot(self, data):
                return False
            def get_latest_snapshot(self):
                return None
            def get_all_snapshots(self):
                return []
        
        print("Creating hybrid backend with simulated GCP outage...")
        local_backend = LocalFileBackend(data_dir=test_dir)
        hybrid = HybridStorageBackend(MockUnavailableBackend(), local_backend)
        
        # Save should succeed using fallback
        print("\nSaving snapshot with GCP unavailable...")
        test_snapshot_3 = TEST_SNAPSHOT.copy()
        test_snapshot_3["timestamp"] = datetime.now().isoformat()
        test_snapshot_3["total_value_eur"] = 300000.0
        
        success = hybrid.save_snapshot(test_snapshot_3)
        assert success, "Should succeed using fallback"
        print("✅ Fallback to local storage works")
        
        # Check status
        print("\nChecking fallback status...")
        status = hybrid.get_sync_status()
        assert not status['primary_available'], "Primary should be unavailable"
        assert status['fallback_available'], "Fallback should be available"
        assert status['pending_syncs'] > 0, "Should have pending syncs"
        print(f"✅ Status correct: {status['pending_syncs']} pending syncs queued")
        
        # Verify data is in local backend
        print("\nVerifying data in local fallback...")
        local_latest = local_backend.get_latest_snapshot()
        assert local_latest is not None, "Local should have snapshot"
        assert local_latest["total_value_eur"] == 300000.0, "Local data should match"
        print("✅ Data saved to local fallback storage")
        
        print("\n✅ All fallback tests passed!")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_storage_module_integration():
    """Test the main storage module integration."""
    print("\n" + "="*60)
    print("TEST 4: Main Storage Module Integration")
    print("="*60)
    
    from agent import storage
    
    # Get backend
    print("Initializing storage backend...")
    backend = storage._get_storage_backend()
    print(f"✅ Backend type: {type(backend).__name__}")
    
    # Test status function
    print("\nGetting storage status...")
    status = storage.get_storage_status()
    print(f"   Backend: {status.get('backend_type', 'Unknown')}")
    print(f"   Available: {status.get('available', False)}")
    if 'primary_available' in status:
        print(f"   Primary (GCP): {status['primary_available']}")
        print(f"   Fallback (local): {status['fallback_available']}")
        print(f"   Pending syncs: {status['pending_syncs']}")
    print("✅ Storage status retrieved successfully")
    
    # Test saving through main interface
    print("\nTesting save through main storage interface...")
    test_snapshot_4 = TEST_SNAPSHOT.copy()
    test_snapshot_4["timestamp"] = datetime.now().isoformat()
    test_snapshot_4["total_value_eur"] = 400000.0
    
    try:
        storage.save_snapshot(test_snapshot_4)
        print("✅ Snapshot saved via main interface")
    except Exception as e:
        print(f"❌ Save failed: {e}")
        raise
    
    # Test retrieval
    print("\nTesting retrieval through main storage interface...")
    latest = storage.get_latest_snapshot()
    assert latest is not None, "Should retrieve snapshot"
    print(f"✅ Retrieved snapshot: {latest.get('timestamp', 'Unknown')}")
    
    print("\n✅ All integration tests passed!")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GCP STORAGE BACKEND TEST SUITE")
    print("="*60)
    print(f"\nTest bucket: gs://{TEST_BUCKET_NAME}")
    print(f"Test region: {TEST_BUCKET_REGION}")
    print("\nThis test suite will:")
    print("  1. Test direct GCP backend access")
    print("  2. Test hybrid backend with dual-write")
    print("  3. Test fallback behavior")
    print("  4. Test main storage module integration")
    print(f"\nNOTE: Test data will be written to gs://{TEST_BUCKET_NAME}")
    print("      All test data will be cleaned up after execution")
    print("      Production bucket is NEVER touched")
    print("="*60)
    
    # Check if test bucket exists
    try:
        creds = load_test_credentials()
        test_backend = GCPStorageBackend(TEST_BUCKET_NAME, creds)
        if not test_backend.is_available():
            print(f"\n❌ ERROR: Test bucket gs://{TEST_BUCKET_NAME} not accessible")
            print(f"\nCreate it with:")
            print(f"  gsutil mb -l {TEST_BUCKET_REGION} gs://{TEST_BUCKET_NAME}")
            exit(1)
        print(f"\n✅ Test bucket accessible")
    except Exception as e:
        print(f"\n❌ ERROR: Cannot access test bucket: {e}")
        exit(1)
    
    try:
        # Run all tests
        test_gcp_backend()
        test_hybrid_backend()
        test_fallback_scenario()
        test_storage_module_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\nYour GCP storage backend is working correctly:")
        print("  ✅ GCP connectivity verified")
        print("  ✅ Dual-write to GCP + local working")
        print("  ✅ Fallback to local storage working")
        print("  ✅ Main storage interface working")
        print("\nNext steps:")
        print("  1. Check your production data in GCS:")
        print("     gsutil cat gs://investment_snapshots/portfolio_history.json | tail -50")
        print("  2. Test MCP tool:")
        print("     uv run python server.py")
        print("     # Then call get_storage_status()")
        print()
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        # ALWAYS cleanup test data, even if tests fail
        cleanup_test_bucket()
