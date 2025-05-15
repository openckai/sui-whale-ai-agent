from typing import List, Dict
from datetime import datetime

class ActivityAnalyzer:
    @staticmethod
    def has_recent_meme_swap(activity_list: List[Dict], meme_coin_symbol: str) -> bool:
        """Check if there are recent swap activities for the meme coin"""
        for act in activity_list:
            types = act.get("activityType", [])
            details = act.get("details", {}).get("detailsDto", {})
            coins = details.get("coins", [])
            for coin in coins:
                if coin.get("symbol", "").lower() == meme_coin_symbol.lower():
                    if "Swap" in types:
                        return True
        return False

    @staticmethod
    def process_swap_activity(activity: Dict, token_price: float) -> Dict:
        """Process swap activity details"""
        details = activity.get("details", {}).get("detailsDto", {})
        coins = details.get("coins", [])
        result = {}
        
        for coin in coins:
            if coin.get("symbol", "").lower() == "lofi":
                amount = coin["amount"]
                result = {
                    'movement_type': 'bought' if amount > 0 else 'sold',
                    'amount': abs(amount),
                    'usd_value': abs(amount) * token_price
                }
                break
        
        return result 