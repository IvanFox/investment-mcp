#!/bin/bash

echo "Alpha Vantage API Key Setup"
echo "============================"
echo ""
echo "This script will store your Alpha Vantage API key securely in macOS Keychain."
echo ""

read -p "Enter your Alpha Vantage API key: " -s api_key
echo ""

if [ -z "$api_key" ]; then
    echo "Error: API key cannot be empty"
    exit 1
fi

security add-generic-password \
    -a "mcp-portfolio-agent" \
    -s "alpha-vantage-api-key" \
    -w "$api_key" \
    -U 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Alpha Vantage API key successfully stored in keychain"
else then
    security delete-generic-password \
        -a "mcp-portfolio-agent" \
        -s "alpha-vantage-api-key" 2>/dev/null

    security add-generic-password \
        -a "mcp-portfolio-agent" \
        -s "alpha-vantage-api-key" \
        -w "$api_key" \
        -U

    if [ $? -eq 0 ]; then
        echo "✓ Alpha Vantage API key successfully updated in keychain"
    else
        echo "✗ Failed to store API key in keychain"
        exit 1
    fi
fi
