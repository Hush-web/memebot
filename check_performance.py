import csv
import os

def print_performance():
    csv_path = 'data/paper_trades.csv'
    if not os.path.exists(csv_path):
        print("No trades yet – run the bot first.")
        return

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        trades = list(reader)

    if not trades:
        print("No trades recorded.")
        return

    wins = sum(1 for t in trades if float(t.get('pnl_percent', 0)) > 0)
    losses = sum(1 for t in trades if float(t.get('pnl_percent', 0)) < 0)
    total_pnl = sum(float(t.get('pnl_percent', 0)) for t in trades)
    total_trades = len(trades)
    win_rate = wins / total_trades * 100 if total_trades else 0

    print("\n" + "="*50)
    print("📊 PAPER TRADING PERFORMANCE")
    print("="*50)
    print(f"  Total Trades:     {total_trades}")
    print(f"  Wins:             {wins} | Losses: {losses}")
    print(f"  Win Rate:         {win_rate:.1f}%")
    print(f"  Total PnL (sum):  {total_pnl:.2f}%")
    print("="*50)

if __name__ == "__main__":
    print_performance()