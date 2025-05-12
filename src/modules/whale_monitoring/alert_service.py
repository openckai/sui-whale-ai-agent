from typing import Dict
from modules.ai_insights.openai_service import WhaleInsightGenerator

class AlertService:
    def __init__(self):
        self.insight_generator = WhaleInsightGenerator()

    def print_whale_movement(self, token_symbol: str, movement_data: Dict, whale_stats: Dict):
        """Print formatted whale movement alert with AI insights"""
        try:
            # Calculate average trade size first
            avg_trade = whale_stats.get('total_volume_usd', 0) / whale_stats.get('total_trades', 1)
            
            # Print header
            print("\n" + "="*80)
            print(f"🚨 {token_symbol} Whale Movement Alert")
            print("="*80)
            
            # Generate and print concise insight
            insight = self.insight_generator.generate_concise_whale_insight(
                stats={
                    "win_rate": whale_stats.get('win_rate', 0),
                    "total_trades": whale_stats.get('total_trades', 0),
                    "total_volume_usd": whale_stats.get('total_volume_usd', 0),
                    "average_trade": avg_trade,
                    "total_pnl_usd": whale_stats.get('total_pnl_usd', 0)
                },
                movement={
                    "token_symbol": token_symbol,
                    "movement_type": movement_data["movement_type"],
                    "usd_value": movement_data["usd_value"],
                    "amount": movement_data["amount"]
                }
            )
            
            # Print main alert
            print(f"🐋 A {token_symbol} whale just {movement_data['movement_type']}ed ${movement_data['usd_value']:,.2f}")
            print(f"📈 Win Rate: {whale_stats.get('win_rate', 0):.1f}% | Total Volume: ${whale_stats.get('total_volume_usd', 0):,.0f}")
            
            # Print insights
            print("\n💡 Quick Analysis:")
            if whale_stats.get('win_rate', 0) > 50:
                print("• High-performing whale with consistent profits - worth following")
                if movement_data['usd_value'] > avg_trade:
                    print("• Larger than usual position - could signal strong conviction")
                else:
                    print("• Testing waters with smaller position - monitor for follow-up moves")
            else:
                print("• Historically underperforming whale - proceed with caution")
                if movement_data['usd_value'] > avg_trade:
                    print("• Unusually large position - potential reversal signal")
                else:
                    print("• Small experimental position - limited market impact")
            
            # Print detailed stats
            print("\n📊 Detailed Stats:")
            print(f"• Total Trades:   {whale_stats.get('total_trades', 0):,}")
            print(f"• Total Volume:   ${whale_stats.get('total_volume_usd', 0):,.2f}")
            print(f"• Average Trade:  ${avg_trade:,.2f}")
            
            # Print footer
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"Error in alert service: {str(e)}") 