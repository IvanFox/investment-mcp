#!/usr/bin/env python3
"""
Test concentration risk without API calls
"""
from agent import storage, risk_analysis

print("🔍 Loading latest portfolio snapshot...")
snapshot = storage.get_latest_snapshot()

if not snapshot:
    print("❌ No portfolio snapshot found")
    exit(1)

assets = snapshot.get('assets', [])
print(f"✅ Found {len(assets)} assets\n")

print("📊 Calculating Concentration Risk...")
concentration = risk_analysis.calculate_concentration_risk(assets)

print("\n" + "="*60)
print("CONCENTRATION RISK ANALYSIS")
print("="*60)
print(f"HHI Score: {concentration['hhi']:.4f}")
print(f"Largest Position: {concentration['largest_position_pct']:.2f}% ({concentration['largest_position_name']})")
print(f"Top 5 Concentration: {concentration['top_5_concentration_pct']:.2f}%")
print(f"Total Positions: {concentration['num_positions']}")

print("\nTop 5 Holdings:")
for i, holding in enumerate(concentration.get('top_holdings', []), 1):
    print(f"  {i}. {holding['name']}: {holding['weight_pct']:.2f}%")

print("\nDiversification Rating:")
hhi = concentration['hhi']
if hhi > 0.25:
    print("  ❌ Highly Concentrated (HHI > 0.25)")
elif hhi > 0.15:
    print("  ⚠️  Moderately Concentrated (HHI 0.15-0.25)")
else:
    print("  ✅ Well Diversified (HHI < 0.15)")
