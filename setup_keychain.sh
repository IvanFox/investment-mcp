#!/bin/bash
# Investment MCP Agent - Keychain Setup Script
# This script helps you securely store Google Cloud Service Account credentials in macOS Keychain

set -e

echo "🔐 Investment MCP Agent - Keychain Setup"
echo "========================================="

# Check if service account file is provided
if [ "$#" -ne 1 ]; then
    echo "❌ Usage: $0 <path-to-service-account.json>"
    echo ""
    echo "Example:"
    echo "  $0 ~/Downloads/investment-mcp-service-account.json"
    echo ""
    echo "This script will:"
    echo "  1. Validate your service account JSON file"
    echo "  2. Store it securely in macOS Keychain"
    echo "  3. Remove the original file for security"
    echo "  4. Test the keychain integration"
    exit 1
fi

SERVICE_ACCOUNT_FILE="$1"

# Check if file exists
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "❌ Error: File '$SERVICE_ACCOUNT_FILE' not found"
    exit 1
fi

echo "📄 Validating service account file..."

# Validate JSON format
if ! jq . "$SERVICE_ACCOUNT_FILE" > /dev/null 2>&1; then
    echo "❌ Error: Invalid JSON format in '$SERVICE_ACCOUNT_FILE'"
    exit 1
fi

# Check required fields
if ! jq -e '.type == "service_account"' "$SERVICE_ACCOUNT_FILE" > /dev/null; then
    echo "❌ Error: File is not a service account JSON"
    exit 1
fi

SERVICE_ACCOUNT_EMAIL=$(jq -r '.client_email' "$SERVICE_ACCOUNT_FILE")
PROJECT_ID=$(jq -r '.project_id' "$SERVICE_ACCOUNT_FILE")

echo "✅ Valid service account file detected"
echo "   Email: $SERVICE_ACCOUNT_EMAIL"
echo "   Project: $PROJECT_ID"

echo ""
echo "🔒 Storing credentials in macOS Keychain..."

# Convert to hex and store in keychain
HEX_CREDENTIALS=$(cat "$SERVICE_ACCOUNT_FILE" | xxd -p | tr -d '\n')

# Store in keychain
security add-generic-password \
    -a "mcp-portfolio-agent" \
    -s "google-sheets-credentials" \
    -w "$HEX_CREDENTIALS" \
    -T "" \
    -U

echo "✅ Credentials stored successfully in Keychain"

# Test retrieval
echo ""
echo "🧪 Testing keychain retrieval..."

if security find-generic-password \
    -a "mcp-portfolio-agent" \
    -s "google-sheets-credentials" \
    -w > /dev/null 2>&1; then
    echo "✅ Keychain retrieval test successful"
else
    echo "❌ Keychain retrieval test failed"
    exit 1
fi

# Securely remove original file
echo ""
echo "🗑️  Removing original service account file for security..."
read -p "Remove '$SERVICE_ACCOUNT_FILE'? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm "$SERVICE_ACCOUNT_FILE"
    echo "✅ Original file removed"
else
    echo "⚠️  Original file kept - remember to delete it manually for security"
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Share your Google Sheet with: $SERVICE_ACCOUNT_EMAIL"
echo "2. Set permission to 'Viewer' for the service account"
echo "3. Run: uv run python check_setup.py"
echo "4. Start the MCP server: uv run python server.py"
echo ""
echo "🔍 To verify setup anytime:"
echo "   uv run python check_setup.py"