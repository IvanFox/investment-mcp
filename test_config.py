#!/usr/bin/env python3
"""
Test suite for configuration system.

Tests configuration loading, validation, environment variable overrides,
and fail-fast behavior.

Usage:
    uv run python test_config.py
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

# Test that config module can be imported
try:
    from agent import config
    from agent.config_models import InvestmentConfig
    from pydantic import ValidationError
except ImportError as e:
    print(f"❌ Failed to import config module: {e}")
    sys.exit(1)


def test_config_loading():
    """Test that config.yaml can be loaded successfully."""
    print("\n🧪 Test 1: Config Loading")
    
    try:
        cfg = config.get_config()
        assert cfg is not None, "Config should not be None"
        assert isinstance(cfg, InvestmentConfig), "Config should be InvestmentConfig instance"
        print("   ✅ Config loaded successfully")
        return True
    except Exception as e:
        print(f"   ❌ Failed to load config: {e}")
        return False


def test_required_fields():
    """Test that all required fields are present."""
    print("\n🧪 Test 2: Required Fields")
    
    try:
        cfg = config.get_config()
        
        # Check Google Sheets config
        assert cfg.google_sheets.sheet_id, "Sheet ID should not be empty"
        print(f"   ✅ Sheet ID: {cfg.google_sheets.sheet_id[:20]}...")
        
        # Check Storage config
        assert cfg.storage.backend in ["hybrid", "gcp", "local"], "Invalid storage backend"
        assert cfg.storage.gcp.bucket_name, "GCP bucket name should not be empty"
        print(f"   ✅ Storage backend: {cfg.storage.backend}")
        print(f"   ✅ GCP bucket: {cfg.storage.gcp.bucket_name}")
        
        # Check ticker mappings
        assert len(cfg.ticker_mappings) > 0, "Should have at least one ticker mapping"
        print(f"   ✅ Ticker mappings: {len(cfg.ticker_mappings)}")
        
        return True
    except AssertionError as e:
        print(f"   ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_environment_overrides():
    """Test that environment variables override config values."""
    print("\n🧪 Test 3: Environment Variable Overrides")
    
    # Save original values
    original_env = {}
    test_env = {
        "INVESTMENT_LOG_LEVEL": "DEBUG",
        "INVESTMENT_GCP_BUCKET": "test-override-bucket",
        "INVESTMENT_STORAGE_BACKEND": "local",
    }
    
    try:
        # Save original values and set test values
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        # Reload config with overrides
        cfg = config.reload_config()
        
        # Verify overrides
        assert cfg.logging.level == "DEBUG", f"Log level should be DEBUG, got {cfg.logging.level}"
        assert cfg.storage.gcp.bucket_name == "test-override-bucket", \
            f"Bucket should be test-override-bucket, got {cfg.storage.gcp.bucket_name}"
        assert cfg.storage.backend == "local", f"Backend should be local, got {cfg.storage.backend}"
        
        print("   ✅ Log level override: DEBUG")
        print("   ✅ GCP bucket override: test-override-bucket")
        print("   ✅ Storage backend override: local")
        
        return True
        
    except AssertionError as e:
        print(f"   ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        
        # Reload config to restore original state
        config.reload_config()


def test_invalid_config():
    """Test that invalid configuration raises ValidationError."""
    print("\n🧪 Test 4: Invalid Config Detection")
    
    try:
        # Create temporary invalid config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
google_sheets:
  sheet_id: ""
storage:
  backend: invalid_backend
  gcp:
    bucket_name: ""
""")
            temp_config_path = f.name
        
        try:
            # Try to load invalid config
            import yaml
            with open(temp_config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            # This should raise ValidationError
            cfg = InvestmentConfig(**yaml_data)
            print("   ❌ Should have raised ValidationError for invalid config")
            return False
            
        except ValidationError as e:
            print("   ✅ Correctly rejected invalid config")
            print(f"   ✅ Validation errors: {len(e.errors())} field(s)")
            return True
        finally:
            # Clean up temp file
            Path(temp_config_path).unlink(missing_ok=True)
            
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_extra_fields_allowed():
    """Test that extra fields in YAML don't break loading (forward compatibility)."""
    print("\n🧪 Test 5: Extra Fields Allowed")
    
    try:
        # Create temporary config with extra fields
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
google_sheets:
  sheet_id: test123
  extra_field: "should be ignored"
storage:
  backend: local
  gcp:
    bucket_name: test-bucket
  local:
    file_path: ./test.json
  future_feature: "some value"
ticker_mappings:
  Test: TST
custom_section:
  feature_flag: true
""")
            temp_config_path = f.name
        
        try:
            import yaml
            with open(temp_config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            cfg = InvestmentConfig(**yaml_data)
            
            assert cfg.google_sheets.sheet_id == "test123"
            assert "Test" in cfg.ticker_mappings
            
            print("   ✅ Extra fields allowed and ignored")
            print("   ✅ Valid fields loaded correctly")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to load config with extra fields: {e}")
            return False
        finally:
            Path(temp_config_path).unlink(missing_ok=True)
            
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_ticker_mapping_integration():
    """Test that ticker mappings work with events_tracker module."""
    print("\n🧪 Test 6: Ticker Mapping Integration")
    
    try:
        from agent.events_tracker import load_ticker_mapping, get_ticker_for_asset
        
        ticker_map = load_ticker_mapping()
        
        # Test loading
        assert len(ticker_map) > 0, "Should have ticker mappings"
        print(f"   ✅ Loaded {len(ticker_map)} ticker mappings")
        
        # Test specific mapping
        if "Apple Inc" in ticker_map:
            ticker = get_ticker_for_asset("Apple Inc")
            assert ticker == "AAPL", f"Apple Inc should map to AAPL, got {ticker}"
            print(f"   ✅ Ticker lookup: Apple Inc -> {ticker}")
        
        # Test missing mapping
        try:
            get_ticker_for_asset("NonExistentStock")
            print("   ❌ Should have raised error for missing mapping")
            return False
        except ValueError as e:
            print("   ✅ Correctly raises error for missing mapping")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_convenience_functions():
    """Test convenience getter functions."""
    print("\n🧪 Test 7: Convenience Functions")
    
    try:
        # Test individual getters
        sheet_id = config.get_sheet_id()
        assert sheet_id, "Sheet ID should not be empty"
        print(f"   ✅ get_sheet_id(): {sheet_id[:20]}...")
        
        bucket_name = config.get_gcp_bucket_name()
        assert bucket_name, "Bucket name should not be empty"
        print(f"   ✅ get_gcp_bucket_name(): {bucket_name}")
        
        ticker_mappings = config.get_ticker_mappings()
        assert len(ticker_mappings) > 0, "Should have ticker mappings"
        print(f"   ✅ get_ticker_mappings(): {len(ticker_mappings)} mappings")
        
        storage_backend = config.get_storage_backend()
        assert storage_backend in ["hybrid", "gcp", "local"], "Invalid backend"
        print(f"   ✅ get_storage_backend(): {storage_backend}")
        
        log_level = config.get_log_level()
        assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR"], "Invalid log level"
        print(f"   ✅ get_log_level(): {log_level}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("Investment MCP Configuration Test Suite")
    print("=" * 70)
    
    tests = [
        test_config_loading,
        test_required_fields,
        test_environment_overrides,
        test_invalid_config,
        test_extra_fields_allowed,
        test_ticker_mapping_integration,
        test_convenience_functions,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - Test {i}: {test.__doc__.strip()}")
    
    print("\n" + "=" * 70)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
