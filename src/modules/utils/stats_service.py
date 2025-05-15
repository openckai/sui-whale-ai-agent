from typing import Dict
from db.models import WalletStats, WhaleMovement, WhaleHolder

class StatsService:
    @staticmethod
    def get_wallet_stats(db, address: str) -> Dict:
        """Get detailed statistics for a wallet address"""
        stats = db.query(WalletStats).filter_by(address=address).first()
        if not stats:
            return {}
        
        movements = db.query(WhaleMovement).join(WhaleHolder).filter(
            WhaleHolder.address == address
        ).order_by(WhaleMovement.timestamp.desc()).all()
        
        holdings = db.query(WhaleHolder).filter_by(address=address).all()
        
        return {
            "address": address,
            "total_volume_usd": stats.total_volume_usd,
            "total_trades": stats.total_trades,
            "win_rate": stats.win_rate,
            "total_pnl_usd": stats.total_pnl_usd,
            "current_holdings": [
                {
                    "token": h.token.symbol,
                    "usd_value": h.usd_value,
                    "percentage": h.percentage
                }
                for h in holdings
            ],
            "recent_movements": [
                {
                    "token": m.token.symbol,
                    "type": m.movement_type,
                    "usd_value": m.usd_value,
                    "timestamp": m.timestamp
                }
                for m in movements[:5]
            ]
        } 