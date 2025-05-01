import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from api_clients import BlockberryClient, InsideXClient
from db.database import get_db
from db.models import Token, WhaleHolder, WhaleMovement, WalletStats

class WhaleDetector:
    """Real-time whale monitoring service"""
    
    def __init__(
        self,
        min_market_cap: float = 1_000_000,
        min_whale_holdings: float = 20_000,
        update_interval: int = 60,  # Default to 1 minute
        manual_tokens: Optional[List[str]] = None
    ):
        self.min_market_cap = min_market_cap
        self.min_whale_holdings = min_whale_holdings
        self.update_interval = update_interval
        self.manual_tokens = manual_tokens or []
        
        # Initialize API clients
        self.blockberry = BlockberryClient()
        self.insidex = InsideXClient()
        
        # Track last update times
        self.last_token_update = datetime.min
        self.last_holder_update = datetime.min
        self.last_movement_check = datetime.min
        
    async def update_monitored_tokens(self, db: Session) -> List[Token]:
        """Update list of monitored tokens based on market cap"""
        current_time = datetime.utcnow()
        
        # Check if we need to update
        if (current_time - self.last_token_update).total_seconds() < self.update_interval:
            return []
        
        print("\nUpdating monitored tokens...")
        
        # Get trending tokens from InsideX
        trending = self.insidex.get_trending_tokens(min_market_cap=self.min_market_cap)
        
        # Combine with manual tokens
        all_tokens = set(self.manual_tokens)
        for token in trending:
            all_tokens.add(token['coin_type'])
        
        # Update database
        updated_tokens = []
        for coin_type in all_tokens:
            token = db.query(Token).filter_by(coin_type=coin_type).first()
            if not token:
                # Get token details
                token_data = self.insidex.get_token_data(coin_type)
                if token_data:
                    token = Token(
                        coin_type=coin_type,
                        symbol=token_data['symbol'],
                        name=token_data.get('name', token_data['symbol']),
                        market_cap=token_data['market_cap'],
                        price_usd=token_data['price'],
                        volume_24h=token_data['volume_24h']
                    )
                    db.add(token)
                    updated_tokens.append(token)
            else:
                # Update existing token
                token_data = self.insidex.get_token_data(coin_type)
                if token_data:
                    token.market_cap = token_data['market_cap']
                    token.price_usd = token_data['price']
                    token.volume_24h = token_data['volume_24h']
                    updated_tokens.append(token)
        
        db.commit()
        self.last_token_update = current_time
        return updated_tokens
    
    async def update_whale_holders(self, db: Session, token: Token) -> List[WhaleHolder]:
        """Update whale holders for a specific token"""
        current_time = datetime.utcnow()
        
        # Check if we need to update
        if (current_time - self.last_holder_update).total_seconds() < self.update_interval:
            return []
        
        print(f"\nUpdating whale holders for {token.symbol}...")
        
        # Get holders from Blockberry
        holders = self.blockberry.get_token_holders(token.coin_type)
        
        # Process only whales
        whales = []
        for holder_data in holders:
            if float(holder_data['usd_value']) >= self.min_whale_holdings:
                # Get or create whale holder
                whale = db.query(WhaleHolder).filter_by(
                    address=holder_data['address'],
                    token_id=token.id
                ).first()
                
                if not whale:
                    whale = WhaleHolder(
                        token_id=token.id,
                        address=holder_data['address'],
                        balance=float(holder_data['balance']),
                        usd_value=float(holder_data['usd_value']),
                        percentage=float(holder_data['percentage'])
                    )
                    db.add(whale)
                else:
                    # Check for movement
                    if whale.balance != float(holder_data['balance']):
                        movement_type = 'buy' if float(holder_data['balance']) > whale.balance else 'sell'
                        movement = WhaleMovement(
                            token_id=token.id,
                            holder_id=whale.id,
                            movement_type=movement_type,
                            amount=abs(float(holder_data['balance']) - whale.balance),
                            usd_value=abs(float(holder_data['usd_value']) - whale.usd_value),
                            timestamp=current_time
                        )
                        db.add(movement)
                        
                        # Update wallet stats
                        self.update_wallet_stats(db, whale.address, movement)
                    
                    # Update holder data
                    whale.balance = float(holder_data['balance'])
                    whale.usd_value = float(holder_data['usd_value'])
                    whale.percentage = float(holder_data['percentage'])
                
                whales.append(whale)
        
        db.commit()
        self.last_holder_update = current_time
        return whales
    
    def update_wallet_stats(self, db: Session, address: str, movement: Optional[WhaleMovement] = None) -> WalletStats:
        """Update wallet statistics based on movements"""
        stats = db.query(WalletStats).filter_by(address=address).first()
        
        if not stats:
            stats = WalletStats(
                address=address,
                total_volume_usd=0,
                total_trades=0,
                total_pnl_usd=0
            )
            db.add(stats)
        
        if movement:
            stats.total_volume_usd += movement.usd_value
            stats.total_trades += 1
            
            # Enhanced PnL calculation
            if movement.movement_type == 'sell':
                # Get average buy price from previous movements
                buy_movements = db.query(WhaleMovement).filter_by(
                    holder_id=movement.holder_id,
                    movement_type='buy'
                ).order_by(WhaleMovement.timestamp.desc()).all()
                
                if buy_movements:
                    avg_buy_price = sum(m.usd_value for m in buy_movements) / sum(m.amount for m in buy_movements)
                    pnl = (movement.usd_value / movement.amount - avg_buy_price) * movement.amount
                    stats.total_pnl_usd += pnl
        
        db.commit()
        return stats
    
    def analyze_wallet(self, db: Session, address: str) -> Dict:
        """Analyze wallet performance and behavior"""
        stats = db.query(WalletStats).filter_by(address=address).first()
        if not stats:
            return {}
        
        # Get recent movements
        movements = db.query(WhaleMovement).join(WhaleHolder).filter(
            WhaleHolder.address == address
        ).order_by(WhaleMovement.timestamp.desc()).limit(10).all()
        
        # Get current holdings
        holdings = db.query(WhaleHolder).filter_by(address=address).all()
        
        # Calculate metrics
        win_rate = stats.win_rate()
        avg_trade_size = stats.total_volume_usd / stats.total_trades if stats.total_trades > 0 else 0
        total_holdings = sum(h.usd_value for h in holdings)
        
        return {
            "address": address,
            "total_volume_usd": stats.total_volume_usd,
            "total_trades": stats.total_trades,
            "win_rate": win_rate,
            "total_pnl_usd": stats.total_pnl_usd,
            "avg_trade_size": avg_trade_size,
            "total_holdings": total_holdings,
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
                    "amount": m.amount,
                    "usd_value": m.usd_value,
                    "timestamp": m.timestamp
                }
                for m in movements
            ]
        }
    
    async def monitor_loop(self):
        """Continuous monitoring loop"""
        while True:
            try:
                with get_db() as db:
                    # Update monitored tokens
                    updated_tokens = await self.update_monitored_tokens(db)
                    
                    # Update whale holders for each token
                    for token in updated_tokens:
                        whales = await self.update_whale_holders(db, token)
                        
                        # Analyze significant movements
                        for whale in whales:
                            analysis = self.analyze_wallet(db, whale.address)
                            if analysis:
                                print(f"\nWhale Alert: {whale.address}")
                                print(f"Current Holdings: ${analysis['total_holdings']:,.2f}")
                                print(f"Win Rate: {analysis['win_rate']:.1f}%")
                                print(f"Total PnL: ${analysis['total_pnl_usd']:,.2f}")
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def start(self):
        """Start the monitoring service"""
        print("\nStarting Whale Detector:")
        print(f"Minimum Market Cap: ${self.min_market_cap:,}")
        print(f"Minimum Whale Holdings: ${self.min_whale_holdings:,}")
        print(f"Update Interval: {self.update_interval} seconds")
        print(f"Manual Tokens: {len(self.manual_tokens)}")
        
        # Run the monitoring loop
        asyncio.run(self.monitor_loop())
