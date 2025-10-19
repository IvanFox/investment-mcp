#!/bin/bash

# Start Investment MCP Server
# This script ensures the server starts with the correct environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR"

# Run the server using uv
exec /opt/homebrew/bin/uv run python "$SCRIPT_DIR/server.py"
