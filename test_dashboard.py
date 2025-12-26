#!/usr/bin/env python3
"""
Test dashboard generation functionality.

Usage:
    uv run python test_dashboard.py
"""

import sys
from pathlib import Path

def test_dashboard_generation():
    """Test that dashboard can be generated from existing snapshots."""
    print("\n🧪 Testing Dashboard Generation")
    print("=" * 60)
    
    try:
        from agent import visualization, storage
        
        # Check if we have snapshots
        snapshots = storage.get_all_snapshots()
        print(f"\n✅ Found {len(snapshots)} snapshots in storage")
        
        if len(snapshots) < 2:
            print(f"\n⚠️  WARNING: Need at least 2 snapshots for dashboard (found {len(snapshots)})")
            print("   Run portfolio analysis first to create snapshots")
            return False
        
        # Test dashboard generation
        print("\n📊 Generating dashboard with all data...")
        result = visualization.generate_portfolio_dashboard(time_period="all")
        
        if not result.get("success"):
            print(f"\n❌ FAILED: {result.get('error')}")
            return False
        
        file_path = result.get("file_path")
        file_url = result.get("file_url")
        snapshot_count = result.get("snapshot_count")
        date_range = result.get("date_range")
        
        print(f"\n✅ Dashboard generated successfully!")
        print(f"   File: {file_path}")
        print(f"   URL: {file_url}")
        print(f"   Snapshots processed: {snapshot_count}")
        print(f"   Date range: {date_range.get('start')} to {date_range.get('end')}")
        
        # Verify file exists
        dashboard_file = Path(file_path)
        if not dashboard_file.exists():
            print(f"\n❌ FAILED: Dashboard file not created at {file_path}")
            return False
        
        file_size = dashboard_file.stat().st_size
        print(f"   File size: {file_size:,} bytes")
        
        if file_size < 1000:
            print(f"\n⚠️  WARNING: Dashboard file seems too small ({file_size} bytes)")
            return False
        
        # Test different time periods
        print("\n📊 Testing time period filtering...")
        for period in ["30d", "90d", "1y"]:
            print(f"   Testing period: {period}...", end=" ")
            result = visualization.generate_portfolio_dashboard(time_period=period)
            if result.get("success"):
                print(f"✅ ({result.get('snapshot_count')} snapshots)")
            else:
                # It's OK if filtering results in too few snapshots
                if "at least 2 snapshots" in result.get("error", ""):
                    print(f"⚠️  Not enough data for {period}")
                else:
                    print(f"❌ {result.get('error')}")
                    return False
        
        print("\n" + "=" * 60)
        print("✅ All dashboard tests passed!")
        print(f"\n🌐 Open dashboard: {file_url}")
        print(f"   Or run: open {file_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import():
    """Test that visualization module can be imported."""
    print("\n🧪 Testing Module Import")
    print("=" * 60)
    
    try:
        from agent import visualization
        print("✅ visualization module imported successfully")
        
        # Check key functions exist
        functions = [
            "generate_portfolio_dashboard",
            "_prepare_portfolio_timeseries",
            "_create_portfolio_value_chart",
            "_generate_dashboard_html"
        ]
        
        for func_name in functions:
            if hasattr(visualization, func_name):
                print(f"✅ Function '{func_name}' exists")
            else:
                print(f"❌ Function '{func_name}' missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Dashboard Generation Test Suite")
    print("=" * 60)
    
    # Test 1: Import
    if not test_import():
        print("\n❌ Import test failed")
        sys.exit(1)
    
    # Test 2: Dashboard generation
    if not test_dashboard_generation():
        print("\n❌ Dashboard generation test failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nDashboard functionality is working correctly!")
    sys.exit(0)
