# Test Bucket Setup Guide

## Overview

The test suite has been updated to use a dedicated test bucket that is completely isolated from your production data. All test data is automatically cleaned up after test execution.

---

## Quick Setup

### 1. Create Test Bucket (One-Time)

```bash
# Default: europe-north1 region (same as production)
gsutil mb -l europe-north1 gs://investment_snapshots_test
```

### 2. Run Tests

```bash
uv run python test_gcp_storage.py
```

That's it! Tests will automatically:
- Use the test bucket
- Write test data
- Clean up all test data after completion

---

## Configuration Options

### Custom Test Bucket Name

```bash
export INVESTMENT_TEST_BUCKET=my-custom-test-bucket
gsutil mb -l europe-north1 gs://my-custom-test-bucket
uv run python test_gcp_storage.py
```

### Custom Region

```bash
export INVESTMENT_TEST_REGION=us-central1
gsutil mb -l us-central1 gs://investment_snapshots_test
uv run python test_gcp_storage.py
```

### Both Custom

```bash
export INVESTMENT_TEST_BUCKET=my-test-bucket
export INVESTMENT_TEST_REGION=us-west1
gsutil mb -l us-west1 gs://my-test-bucket
uv run python test_gcp_storage.py
```

---

## What Changed

### Before (UNSAFE ⚠️)
- Tests wrote to production bucket `investment_snapshots`
- Created snapshots with `"name": "Test Asset"`
- Required manual cleanup from production bucket

### After (SAFE ✅)
- Tests write to dedicated test bucket `investment_snapshots_test`
- Production bucket is NEVER touched
- Automatic cleanup via `finally` block
- Environment variable configuration

---

## Safety Features

### 1. Environment Variable Override
Tests explicitly set `INVESTMENT_GCP_BUCKET` to test bucket at startup:
```python
os.environ['INVESTMENT_GCP_BUCKET'] = TEST_BUCKET_NAME
```

### 2. Bucket Existence Check
Tests verify bucket exists before running:
```
✅ Test bucket accessible
```
Or fail early with setup instructions:
```
❌ ERROR: Test bucket gs://investment_snapshots_test not accessible

Create it with:
  gsutil mb -l europe-north1 gs://investment_snapshots_test
```

### 3. Automatic Cleanup
Cleanup runs in `finally` block - executes even if tests fail:
```python
finally:
    cleanup_test_bucket()
```

### 4. Clear Logging
Test output shows which bucket is being used:
```
Test bucket: gs://investment_snapshots_test
Production bucket is NEVER touched
```

---

## Files Modified

### `agent/backends/gcp_storage.py`
**Added:** `delete_all_snapshots()` method
- Deletes entire `portfolio_history.json` file from bucket
- Marked with WARNING in docstring for test use only
- Safe to use on test bucket (that's its purpose!)
- Returns `True` if successful or file doesn't exist

### `test_gcp_storage.py`
**Updated:**
- Environment variable configuration for test bucket
- All hardcoded `"investment_snapshots"` replaced with `TEST_BUCKET_NAME`
- Added `cleanup_test_bucket()` function
- Added `finally` block to ensure cleanup
- Added bucket existence check before running tests
- Updated docstring with setup instructions

### `test_storage_safety.py`
**Deleted:** Redundant test file
- Tests were for old local-only storage system
- Referenced non-existent constants
- Functionality already covered by `test_gcp_storage.py`

---

## Verification Checklist

After running tests, verify:

1. **Test bucket is empty:**
   ```bash
   gsutil ls gs://investment_snapshots_test/
   # Should output nothing (empty bucket)
   ```

2. **Production bucket unchanged:**
   ```bash
   gsutil ls gs://investment_snapshots/
   # Should show: portfolio_history.json (unchanged)
   ```

3. **Tests passed:**
   ```
   🎉 ALL TESTS PASSED!
   ✅ Test data deleted from gs://investment_snapshots_test
   ```

---

## Troubleshooting

### "Test bucket not accessible"

**Cause:** Bucket doesn't exist

**Fix:**
```bash
gsutil mb -l europe-north1 gs://investment_snapshots_test
```

### "Permission denied"

**Cause:** Service account lacks permissions on test bucket

**Fix:** Test bucket uses same credentials as production, so if production works, test should too. If not:
```bash
# Get service account email
cat ~/.config/gcloud/credentials.json | grep client_email

# Grant permissions
gsutil iam ch serviceAccount:YOUR-SA@PROJECT.iam.gserviceaccount.com:objectAdmin gs://investment_snapshots_test
```

### Cleanup fails (non-critical)

**Impact:** Test data remains in test bucket

**Fix:** Manual cleanup:
```bash
gsutil rm gs://investment_snapshots_test/portfolio_history.json
```

**Note:** Cleanup failures don't cause test failures - just a warning is shown.

---

## Test Data Created

During test execution, the following test snapshots are created (then deleted):

1. **Test 1:** 1 snapshot with 100,000 EUR
2. **Test 2:** 1 snapshot with 200,000 EUR  
3. **Test 3:** 1 snapshot with 300,000 EUR (local only, simulated GCP outage)
4. **Test 4:** 1 snapshot with 400,000 EUR

All snapshots have `"name": "Test Asset"` in the assets array.

**After cleanup:** Test bucket is completely empty.

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `INVESTMENT_TEST_BUCKET` | `investment_snapshots_test` | Test bucket name |
| `INVESTMENT_TEST_REGION` | `europe-north1` | Region for bucket creation |
| `INVESTMENT_GCP_BUCKET` | (auto-set to test bucket) | Config override for tests |

---

## Next Steps

1. **Create test bucket:**
   ```bash
   gsutil mb -l europe-north1 gs://investment_snapshots_test
   ```

2. **Run tests:**
   ```bash
   uv run python test_gcp_storage.py
   ```

3. **Verify cleanup:**
   ```bash
   gsutil ls gs://investment_snapshots_test/
   # Should be empty
   ```

4. **Check production untouched:**
   ```bash
   gsutil cat gs://investment_snapshots/portfolio_history.json | grep "Test Asset"
   # Should output nothing (no test data in production)
   ```

---

## Questions?

- Test bucket not accessible? → Create it with `gsutil mb`
- Tests fail? → Check error message for specific issue
- Cleanup doesn't run? → Check `finally` block in test output
- Production data concerned? → Tests never use production bucket anymore!

**Production bucket is completely safe.** ✅
