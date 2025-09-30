#!/usr/bin/env python3
"""
Setup verification and status check for Investment MCP Agent.
Run this script to verify your configuration and test the system.
"""

import json
import sys

def check_credentials():
    """Check credentials configuration."""
    try:
        with open('credentials.json', 'r') as f:
            credentials = json.load(f)
        
        if credentials.get('type') == 'service_account':
            email = credentials.get('client_email')
            project = credentials.get('project_id')
            print(f"✅ Service Account: {email}")
            print(f"📋 Project: {project}")
            return email
        else:
            print("❌ Invalid credentials format")
            return None
    except Exception as e:
        print(f"❌ Credentials error: {e}")
        return None

def check_sheet_config():
    """Check sheet configuration."""
    try:
        with open('sheet-details.json', 'r') as f:
            sheet_details = json.load(f)
        
        sheet_id = sheet_details.get('sheetId')
        gid = sheet_details.get('gid')
        print(f"✅ Sheet ID: {sheet_id}")
        print(f"📊 GID: {gid}")
        return sheet_id
    except Exception as e:
        print(f"❌ Sheet config error: {e}")
        return None

def test_system():
    """Test system functionality."""
    try:
        from agent import sheets_connector, main
        
        print("🔑 Testing authentication...")
        service = sheets_connector.get_sheets_service()
        print("✅ Authentication successful")
        
        print("📊 Testing sheet access...")
        result = main._run_weekly_analysis()
        print("✅ System test successful!")
        return True
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "permission" in error_msg.lower():
            print("❌ Permission denied - sheet not shared with service account")
        else:
            print(f"❌ System test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Investment MCP Agent - System Check")
    print("=" * 45)
    
    print("\n1. Checking credentials...")
    service_email = check_credentials()
    
    print("\n2. Checking sheet configuration...")
    sheet_id = check_sheet_config()
    
    if service_email and sheet_id:
        print(f"\n3. Testing system...")
        if test_system():
            print(f"\n🎉 System is fully operational!")
            print(f"🛠️  Start MCP server: uv run python server.py")
        else:
            print(f"\n📧 Share your sheet with: {service_email}")
            print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    else:
        print(f"\n❌ Configuration incomplete")
    
    print("=" * 45)