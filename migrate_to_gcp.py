#!/usr/bin/env python3
"""
One-time migration script to upload existing portfolio history to GCP.

This script uploads your local portfolio_history.json to Google Cloud Storage
for automatic cross-machine synchronization.
"""

import json
import logging
import os
import sys
import subprocess

from google.cloud import storage
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = "investment_snapshots"
BLOB_NAME = "portfolio_history.json"
LOCAL_FILE = "portfolio_history.json"


def load_credentials():
    """Load GCP credentials from macOS Keychain."""
    try:
        logger.info("Loading GCP credentials from Keychain...")
        result = subprocess.run(
            ["security", "find-generic-password", "-a", "mcp-portfolio-agent", 
             "-s", "google-sheets-credentials", "-w"],
            capture_output=True,
            text=True,
            check=True
        )
        
        hex_data = result.stdout.strip()
        json_bytes = bytes.fromhex(hex_data)
        json_str = json_bytes.decode('utf-8')
        
        credentials = json.loads(json_str)
        logger.info("✅ Credentials loaded successfully")
        return credentials
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to load credentials from Keychain: {e}")
        logger.error("Make sure credentials are stored with:")
        logger.error("  ./setup_keychain.sh path/to/credentials.json")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to parse credentials: {e}")
        raise


def main():
    """Upload existing portfolio history to GCP."""
    
    print("=" * 60)
    print("GCP Cloud Storage Migration")
    print("=" * 60)
    print()
    
    # Check if local file exists
    if not os.path.exists(LOCAL_FILE):
        logger.error(f"❌ Local file {LOCAL_FILE} not found. Nothing to migrate.")
        print()
        print("To create your first snapshot, run:")
        print("  uv run python -m agent.main")
        sys.exit(1)
    
    # Load local history
    logger.info(f"Reading local history from {LOCAL_FILE}...")
    try:
        with open(LOCAL_FILE, 'r') as f:
            history = json.load(f)
        
        if not isinstance(history, list):
            logger.error(f"❌ Invalid format: expected list, got {type(history).__name__}")
            sys.exit(1)
        
        logger.info(f"✅ Found {len(history)} snapshots in local file")
        
        # Show date range
        if history:
            first_date = history[0].get('timestamp', 'Unknown')
            last_date = history[-1].get('timestamp', 'Unknown')
            logger.info(f"   Date range: {first_date} to {last_date}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in {LOCAL_FILE}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to read {LOCAL_FILE}: {e}")
        sys.exit(1)
    
    print()
    
    # Load credentials
    try:
        creds_dict = load_credentials()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
    except Exception as e:
        logger.error(f"❌ Failed to initialize credentials: {e}")
        sys.exit(1)
    
    # Initialize GCS client
    logger.info(f"Connecting to GCS bucket: {BUCKET_NAME}...")
    try:
        client = storage.Client(credentials=credentials)
        bucket = client.bucket(BUCKET_NAME)
        
        # Verify bucket exists
        if not bucket.exists():
            logger.error(f"❌ Bucket '{BUCKET_NAME}' does not exist or is not accessible")
            logger.error("   Please verify:")
            logger.error("   1. Bucket name is correct")
            logger.error("   2. Service account has Storage Object Admin permissions")
            sys.exit(1)
        
        logger.info(f"✅ Connected to bucket: gs://{BUCKET_NAME}")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to GCS: {e}")
        sys.exit(1)
    
    print()
    
    # Check if file already exists in GCS
    blob = bucket.blob(BLOB_NAME)
    if blob.exists():
        logger.warning(f"⚠️  File {BLOB_NAME} already exists in GCS!")
        
        # Download and show what's there
        try:
            existing_content = blob.download_as_text()
            existing_history = json.loads(existing_content)
            logger.info(f"   Existing file has {len(existing_history)} snapshots")
            
            if existing_history:
                first_date = existing_history[0].get('timestamp', 'Unknown')
                last_date = existing_history[-1].get('timestamp', 'Unknown')
                logger.info(f"   Date range: {first_date} to {last_date}")
        except:
            logger.warning("   Could not read existing file")
        
        print()
        response = input("Overwrite existing file? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Migration cancelled")
            sys.exit(0)
        print()
    
    # Upload to GCS
    logger.info(f"Uploading to gs://{BUCKET_NAME}/{BLOB_NAME}...")
    try:
        json_content = json.dumps(history, indent=2, ensure_ascii=False)
        blob.upload_from_string(json_content, content_type="application/json")
        
        logger.info("✅ Upload successful!")
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Uploaded {len(history)} snapshots to GCS")
    print(f"  - Local file: {os.path.abspath(LOCAL_FILE)}")
    print(f"  - GCS location: gs://{BUCKET_NAME}/{BLOB_NAME}")
    print()
    print("Next steps:")
    print("  1. Verify data in GCS:")
    print(f"     gsutil cat gs://{BUCKET_NAME}/{BLOB_NAME} | head -50")
    print()
    print("  2. Test the storage system:")
    print("     uv run python test_gcp_storage.py")
    print()
    print("  3. Check storage status via MCP:")
    print("     # Start server: uv run python server.py")
    print("     # Then call: get_storage_status()")
    print()
    print("Note: Local file will continue to serve as automatic backup")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
