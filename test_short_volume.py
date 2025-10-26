#!/usr/bin/env python3
import sys
from agent.short_volume import get_short_volume_for_ticker

def test_short_volume():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"\n{'='*80}")
    print(f"Testing Short Volume for {ticker} (last {days} days)")
    print(f"{'='*80}\n")
    
    try:
        result = get_short_volume_for_ticker(ticker, days)
        
        if not result.get('success'):
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            if 'help' in result:
                print(f"Help: {result['help']}")
            return
        
        print(f"✅ Ticker: {result['ticker']}")
        
        metrics = result.get('metrics', {})
        if metrics.get('data_points', 0) == 0:
            print(f"\n{result.get('message', 'No data available')}")
            return
        
        print(f"\n📊 Metrics ({metrics['data_points']} days)")
        print(f"  Average Short Ratio: {metrics['avg_short_ratio']:.2f}%")
        print(f"  7-Day Average: {metrics['avg_7day']:.2f}%")
        print(f"  30-Day Average: {metrics['avg_30day']:.2f}%")
        print(f"  Latest ({metrics['latest_date']}): {metrics['latest_short_ratio']:.2f}%")
        print(f"  Trend: {metrics['trend']}")
        
        short_interest = result.get('short_interest', {})
        if short_interest.get('shortPercentOfFloat') is not None:
            print(f"\n📈 Short Interest")
            print(f"  Short % of Float: {short_interest['shortPercentOfFloat'] * 100:.2f}%")
            if short_interest.get('daysToCover'):
                print(f"  Days to Cover: {short_interest['daysToCover']:.1f} days")
            if short_interest.get('settlementDate'):
                print(f"  As of: {short_interest['settlementDate']}")
        
        risk = result.get('risk_analysis', {})
        if risk:
            print(f"\n⚠️  Risk Analysis")
            print(f"  Risk Level: {risk['risk_emoji']} {risk['risk_level']}")
            print(f"  Description: {risk['description']}")
            print(f"  Risk Score: {risk['score']}")
            if risk.get('factors'):
                print(f"  Factors:")
                for factor in risk['factors']:
                    print(f"    - {factor}")
        
        data_records = result.get('data', [])
        if data_records:
            print(f"\n📅 Recent Activity (last 5 days)")
            sorted_records = sorted(data_records, key=lambda x: x.get('marketDate', ''), reverse=True)
            for i, record in enumerate(sorted_records[:5], 1):
                date = record.get('marketDate', 'Unknown')
                short_vol = record.get('shortVolume', 0)
                total_vol = record.get('totalVolume', 0)
                ratio = record.get('shortVolumeRatio', 0) * 100
                print(f"  {i}. {date}: {short_vol:,} / {total_vol:,} ({ratio:.2f}%)")
        
        print(f"\n{'='*80}\n")
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_short_volume()
