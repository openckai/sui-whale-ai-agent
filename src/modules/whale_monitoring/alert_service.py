from typing import Dict

class AlertService:
    @staticmethod
    def print_whale_movement(token_symbol: str, movement_data: Dict, whale_stats: Dict):
        """Print formatted whale movement alert"""
        print(f"\n🚨 {token_symbol} Whale Movement Detected 🚨")
        print(
            f"A ${token_symbol} whale just "
            f"{movement_data['movement_type']} "
            f"${movement_data['usd_value']:,.2f} worth of ${token_symbol}"
        )
        
        if whale_stats:
            print("\nInsights on this whale:")
            print(f"🔹 Win Rate: {whale_stats['win_rate']:.2f}%")
            print(f"🔹 Total Trades: {whale_stats['total_trades']}")
            pnl_str = 'Positive' if whale_stats['total_pnl_usd'] > 0 else 'Negative'
            avg_trade = whale_stats['total_volume_usd'] / whale_stats['total_trades'] if whale_stats['total_trades'] > 0 else 0
            print(f"🔹 PnL: {pnl_str}")
            print(f"🔹 Average Trade: ${avg_trade:,.2f}")
            print(f"🔹 Total Volume: ${whale_stats['total_volume_usd']:,.2f}")
        else:
            print("🔹 No stats available for this whale.")
        print("-" * 30) 