#!/bin/bash

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <your-fintel-api-key>"
    echo "  Example: $0 sk_abc123..."
    echo ""
    echo "📝 To get your API key:"
    echo "  1. Login to https://fintel.io"
    echo "  2. Go to https://fintel.io/u/dev"
    echo "  3. Click 'Generate Key'"
    exit 1
fi

FINTEL_API_KEY="$1"

echo "🔒 Storing Fintel API key in macOS Keychain..."

security delete-generic-password \
    -a "mcp-portfolio-agent" \
    -s "fintel-api-key" 2>/dev/null || true

security add-generic-password \
    -a "mcp-portfolio-agent" \
    -s "fintel-api-key" \
    -w "$FINTEL_API_KEY" \
    -U

if [ $? -eq 0 ]; then
    echo "✅ Fintel API key stored successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "  1. The key is now stored securely in macOS Keychain"
    echo "  2. You can now use insider trading tools in the MCP agent"
    echo "  3. Test with: get_insider_trades('AAPL')"
else
    echo "❌ Failed to store API key in keychain"
    exit 1
fi
