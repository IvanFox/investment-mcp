#!/usr/bin/env python3
"""
Quick test script for running risk analysis locally
"""
import sys
import logging
from agent import storage, risk_analysis, reporting

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("🔍 Loading latest portfolio snapshot...")
    latest_snapshot = storage.get_latest_snapshot()
    
    if not latest_snapshot:
        print("❌ No portfolio snapshot found. Run portfolio analysis first.")
        return 1
    
    portfolio_assets = latest_snapshot.get('assets', [])
    print(f"✅ Found {len(portfolio_assets)} assets in portfolio\n")
    
    print("📊 Running comprehensive risk analysis...")
    print("⏳ This may take several minutes due to API rate limits...")
    print("💡 Tip: Price data is cached for 24 hours to speed up subsequent runs\n")
    
    risk_data = risk_analysis.analyze_portfolio_risk(portfolio_assets)
    
    if not risk_data.get('success'):
        print(f"\n❌ Risk analysis failed: {risk_data.get('error')}")
        print(f"Error type: {risk_data.get('error_type')}")
        return 1
    
    print("\n✅ Risk analysis completed!\n")
    print("=" * 80)
    
    markdown_report = reporting.format_risk_report_markdown(risk_data)
    print(markdown_report)
    
    print("\n" + "=" * 80)
    print(f"📈 Assets analyzed: {risk_data.get('assets_analyzed')} of {risk_data.get('total_assets')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
