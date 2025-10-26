#!/usr/bin/env python3
"""
Setup verification and status check for Investment MCP Agent.
Run this script to verify your keychain configuration and test the system.
"""

import json
import sys

def check_credentials():
    """Check keychain credentials configuration."""
    try:
        from agent.sheets_connector import load_credentials_from_keychain
        
        credentials = load_credentials_from_keychain()
        
        if credentials.get('type') == 'service_account':
            email = credentials.get('client_email')
            project = credentials.get('project_id')
            print(f"✅ Service Account: {email}")
            print(f"📋 Project: {project}")
            return email
        else:
            print("❌ Invalid credentials format in keychain")
            return None
    except Exception as e:
        print(f"❌ Keychain credentials error: {e}")
        print("💡 Run this command to store credentials:")
        print("   security add-generic-password \\")
        print("     -a 'mcp-portfolio-agent' \\")
        print("     -s 'google-sheets-credentials' \\")
        print("     -w \"$(cat your-service-account.json | xxd -p | tr -d '\\n')\" \\")
        print("     -T \"\"")
        return None

def check_alpha_vantage_key():
    """Check Alpha Vantage API key."""
    try:
        from agent.events_tracker import load_alpha_vantage_api_key
        
        api_key = load_alpha_vantage_api_key()
        masked_key = api_key[:8] + "..." if len(api_key) > 8 else "..."
        print(f"✅ Alpha Vantage API Key: {masked_key}")
        return True
    except Exception as e:
        print(f"❌ Alpha Vantage API key error: {e}")
        print("💡 Run: ./setup_alpha_vantage.sh")
        return False

def check_fintel_key():
    """Check Fintel API key."""
    try:
        from agent.insider_trading import load_fintel_api_key
        
        api_key = load_fintel_api_key()
        masked_key = api_key[:8] + "..." if len(api_key) > 8 else "..."
        print(f"✅ Fintel API Key: {masked_key}")
        return True
    except Exception as e:
        print(f"❌ Fintel API key error: {e}")
        print("💡 Run: ./setup_fintel.sh")
        return False

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
    
    print("\n1. Checking keychain credentials...")
    service_email = check_credentials()
    
    print("\n2. Checking Alpha Vantage API key...")
    has_alpha_vantage = check_alpha_vantage_key()
    
    print("\n3. Checking Fintel API key...")
    has_fintel = check_fintel_key()
    
    print("\n4. Checking sheet configuration...")
    sheet_id = check_sheet_config()
    
    if service_email and sheet_id:
        print(f"\n5. Testing system...")
        if test_system():
            print(f"\n🎉 System is fully operational!")
            print(f"🛠️  Start MCP server: uv run python server.py")
        else:
            print(f"\n📧 Share your sheet with: {service_email}")
            print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    else:
        print(f"\n❌ Configuration incomplete")
        if not service_email:
            print("🔐 Store Service Account credentials in Keychain first")
    
    print("=" * 45)