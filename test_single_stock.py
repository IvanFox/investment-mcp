#!/usr/bin/env python3
"""
Test fetching data for a single stock
"""
from agent import risk_analysis

print("🔑 Loading API key...")
try:
    api_key = risk_analysis.load_alpha_vantage_api_key()
    print("✅ API key loaded successfully\n")
except Exception as e:
    print(f"❌ Failed to load API key: {e}")
    exit(1)

print("📊 Fetching historical prices for AAPL (this may take 30-60 seconds)...")
prices = risk_analysis.fetch_historical_prices('AAPL', api_key, lookback_days=90)

if prices is not None and len(prices) > 0:
    print(f"✅ Successfully fetched {len(prices)} days of price data\n")
    print("Sample data (last 5 days):")
    print(prices.tail())
    
    returns = risk_analysis.calculate_returns(prices)
    print(f"\n📈 Calculated {len(returns)} daily returns")
    print(f"Mean daily return: {returns.mean():.4%}")
    print(f"Daily volatility: {returns.std():.4%}")
    print(f"Annualized volatility: {returns.std() * (252**0.5):.2%}")
else:
    print("❌ Failed to fetch prices")
