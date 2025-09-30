#!/usr/bin/env python3
"""
FastMCP Server for Investment Portfolio Agent

Run this script to start the MCP server that provides portfolio analysis tools.
"""

import logging
import sys
import os

# Add the agent module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.main import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        # Start the MCP server
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 Investment MCP Agent shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        sys.exit(1)