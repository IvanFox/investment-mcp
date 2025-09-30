# Investment MCP Agent

An automated portfolio monitoring and performance analysis system built with FastMCP.

## Overview

This MCP agent fetches portfolio data from Google Sheets, generates weekly performance snapshots, and provides detailed analysis including:

- Portfolio value tracking over time
- Top performers and underperformers 
- New and sold positions tracking
- Realized gains/losses calculation
- Automated weekly reports in Markdown format

## Features

- **Automated Data Fetching**: Connects to Google Sheets API to fetch portfolio data
- **Multi-Currency Support**: Handles USD, EUR, and GBP with automatic conversion
- **Performance Analysis**: Week-over-week comparison with detailed insights
- **Portfolio History**: Persistent storage in JSON format
- **Rich Reporting**: Formatted Markdown reports with emojis and clear sections

## Setup

1. Place your Google API credentials in `credentials.json`
2. Configure your sheet details in `sheet-details.json`
3. Install dependencies: `uv sync`
4. Run the agent to start monitoring

## Usage

The agent provides several tools:

- `run_portfolio_analysis()`: Manually trigger a portfolio analysis
- `get_portfolio_status()`: Get current portfolio status
- `get_portfolio_history_summary()`: View historical performance summary

## Technical Stack

- **Language**: Python 3.12+
- **Framework**: FastMCP
- **APIs**: Google Sheets API
- **Storage**: JSON file persistence
- **Package Manager**: uv