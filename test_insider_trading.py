#!/usr/bin/env python3
import sys
from agent.insider_trading import get_insider_trades_for_ticker

def test_single_ticker():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print(f"\n{'='*80}")
    print(f"Testing insider trades for {ticker}")
    print(f"{'='*80}\n")
    
    try:
        result = get_insider_trades_for_ticker(ticker)
        
        if not result.get('success'):
            print(f"Error: {result.get('error', 'Unknown error')}")
            if 'help' in result:
                print(f"Help: {result['help']}")
            return
        
        print(f"Ticker: {result['ticker']}")
        print(f"Total Trades (90 days): {result['total_trades']}")
        
        if result['total_trades'] == 0:
            print(f"\n{result.get('message', 'No trades found')}")
        else:
            stats = result['statistics']
            print(f"\nBuys: {stats['total_buys']}")
            print(f"Sells: {stats['total_sells']}")
            print(f"Total Buy Value: ${stats['buy_value_usd']:,.2f}")
            print(f"Total Sell Value: ${stats['sell_value_usd']:,.2f}")
            print(f"Net Sentiment: {stats['net_sentiment']}")
            
            if result['trades']:
                print(f"\nRecent Trades (last 5):")
                for i, trade in enumerate(result['trades'][:5], 1):
                    code = trade.get('code', 'Unknown')
                    date = trade.get('transactionDate', trade.get('fileDate', 'Unknown'))
                    insider = trade.get('name', 'Unknown')
                    shares = trade.get('shares', 0)
                    value = trade.get('value', 0)
                    print(f"  {i}. {date} - {insider}: {code} {shares:,.0f} shares (${value:,.2f})")
        
        print(f"\nData URL: {result['url']}")
        print(f"Attribution: Data provided by Fintel.io")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_ticker()
