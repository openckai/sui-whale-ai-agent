import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os

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
        self.blockberry = BlockberryClient(api_key=os.getenv("BLOCKBERRY_API_KEY"))
        self.insidex = InsideXClient(api_key=os.getenv("INSIDEX_API_KEY"))
        
        # Track last update times
        self.last_token_update = datetime.min
        self.last_holder_update = datetime.min
        self.last_movement_check = datetime.min
        
        # Known utility tokens to exclude from monitoring
        self.utility_tokens = {
            "0x2::sui::SUI",  # SUI
            "0x2::sui::BLUE",  # BLUE
            # Add more utility tokens as needed
        }
        
    def is_meme_token(self, token_data: Dict) -> bool:
        """
        Determine if a token is likely a meme token based on characteristics
        
        Args:
            token_data: Token data from API
            
        Returns:
            bool: True if token is likely a meme token
        """
        # Check if token is in utility tokens list
        if token_data.get('coin_type') in self.utility_tokens:
            return False
            
        # Meme token characteristics
        name = token_data.get('name', '').lower()
        symbol = token_data.get('symbol', '').lower()
        
        # Check for meme-like names/symbols
        meme_keywords = ['meme', 'pepe', 'doge', 'shib', 'inu', 'wojak', 'chad', 'based']
        if any(keyword in name or keyword in symbol for keyword in meme_keywords):
            return True
            
        # Check for low market cap (meme tokens often have lower market caps)
        market_cap = float(token_data.get('marketCap', 0))
        if market_cap < 10_000_000:  # Less than $10M market cap
            return True
            
        return False
        
    async def update_monitored_tokens(self, db: Session) -> List[Token]:
        """Update list of monitored tokens based on market cap"""
        current_time = datetime.utcnow()
        
        # Check if we need to update
        if (current_time - self.last_token_update).total_seconds() < self.update_interval:
            return []
        
        print("\nUpdating monitored tokens...")
        
        try:
            # Get trending tokens
            trending = self.insidex.get_trending_tokens(min_market_cap=self.min_market_cap)
            
            # Prioritize meme tokens
            meme_tokens = []
            utility_tokens = []
            
            for token in trending:
                if self.is_meme_token(token):
                    meme_tokens.append(token)
                else:
                    utility_tokens.append(token)
                    
            # Combine with manual tokens, prioritizing meme tokens
            all_tokens = set(self.manual_tokens)
            for token in meme_tokens + utility_tokens:
                all_tokens.add(token['coin_type'])
            
            print(f"Found {len(meme_tokens)} meme tokens and {len(utility_tokens)} utility tokens")
            
        except Exception as e:
            print(f"Error fetching trending tokens: {e}")
            all_tokens = set(self.manual_tokens)
        
        # Update database
        updated_tokens = []
        for coin_type in all_tokens:
            token = db.query(Token).filter_by(coin_type=coin_type).first()
            if not token:
                # Get token details
                token_data = await self.blockberry.get_token_details_async(coin_type)
                if token_data:
                    try:
                        token = Token(
                            coin_type=coin_type,
                            symbol=token_data['symbol'],
                            name=token_data.get('name', token_data['symbol']),
                            market_cap=float(token_data.get('marketCap') or 0),
                            price_usd=float(token_data.get('price') or 0),
                            volume_24h=float(token_data.get('totalVolume') or 0),
                            is_meme_token=self.is_meme_token(token_data)
                        )
                        db.add(token)
                        updated_tokens.append(token)
                    except (TypeError, ValueError) as e:
                        print(f"Error creating token {coin_type}: {e}")
                        continue
            else:
                # Update existing token
                token_data = await self.blockberry.get_token_details_async(coin_type)
                if token_data:
                    try:
                        token.market_cap = float(token_data.get('marketCap') or 0)
                        token.price_usd = float(token_data.get('price') or 0)
                        token.volume_24h = float(token_data.get('totalVolume') or 0)
                        token.is_meme_token = self.is_meme_token(token_data)
                        updated_tokens.append(token)
                    except (TypeError, ValueError) as e:
                        print(f"Error updating token {coin_type}: {e}")
                        continue
        
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
        holders = await self.blockberry.get_token_holders_async(token.coin_type)
        
        # Process only whales
        whales = []
        for holder_data in holders:
            if float(holder_data['usd_value']) >= self.min_whale_holdings:
                # Get or create whale holder
                whale = db.query(WhaleHolder).filter_by(
                    address=holder_data['address'],
                    token_id=token.id
                ).first()

                print(f"Whale holder for line 170: {whale}")
                
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
        try:
            # Create stats if not exists
            if not stats:
                stats = WalletStats(address=address)
            db.add(stats)
            
            # Get detailed trader stats from InsideX
            try:
                trader_stats = self.insidex.get_trader_stats(address)
                
                if trader_stats:
                    stats.total_trades = trader_stats.get('total_trades', 0)
                    stats.total_pnl_usd = trader_stats.get('pnl', 0)
                    stats.total_volume_usd = trader_stats.get('volume', 0) 
                    stats.win_rate = trader_stats.get('win_rate', 0)
            except Exception as e:
                print(f"Error getting trader stats from InsideX: {e}")
        
        except Exception as e:
            print(f"Error getting trader stats from InsideX: {e}")
        
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
                                # Get recent movements for this whale
                                recent_movements = analysis.get('recent_movements', [])
                                if recent_movements:
                                    latest_movement = recent_movements[0]  # Most recent movement
                                    
                                    # Enhanced alert for meme tokens
                                    if token.is_meme_token:
                                        print("\n" + "="*80)
                                        print("🚨 WHALE ALERT: MEME TOKEN MOVEMENT 🚨")
                                        print("="*80)
                                        print(f"Token: {token.symbol} ({token.name})")
                                        print(f"Type: {'BUY' if latest_movement['type'] == 'buy' else 'SELL'}")
                                        print(f"Amount: ${latest_movement['usd_value']:,.2f}")
                                        print(f"Time: {latest_movement['timestamp']}")
                                        
                                        print("\n🐋 WHALE DETAILS:")
                                        print(f"Address: {whale.address}")
                                        print(f"Current Holdings: ${whale.usd_value:,.2f}")
                                        print(f"Percentage of Supply: {whale.percentage:.2f}%")
                                        print(f"Total Portfolio Value: ${analysis['total_holdings']:,.2f}")
                                        print(f"Win Rate: {analysis['win_rate']:.1f}%")
                                        print(f"Total PnL: ${analysis['total_pnl_usd']:,.2f}")
                                        print(f"Average Trade Size: ${analysis['avg_trade_size']:,.2f}")
                                        
                                        print("\n📊 CURRENT HOLDINGS:")
                                        for holding in analysis['current_holdings']:
                                            print(f"- {holding['token']}: ${holding['usd_value']:,.2f} ({holding['percentage']:.2f}%)")
                                        
                                        print("\n📈 RECENT ACTIVITY (Last 3 Movements):")
                                        for move in recent_movements[:3]:
                                            print(f"- {move['timestamp']}: {move['type'].upper()} ${move['usd_value']:,.2f}")
                                            print(f"  Token: {move['token']}")
                                            print(f"  Amount: {move['amount']:,.2f}")
                                        print("="*80 + "\n")
                                    else:
                                        # For utility tokens, only alert on very large movements
                                        if analysis['total_holdings'] > 100_000:  # $100k+ holdings
                                            print("\n" + "-"*60)
                                            print("⚠️ Utility Token Movement")
                                            print(f"Token: {token.symbol} ({token.name})")
                                            print(f"Address: {whale.address}")
                                            print(f"Holdings: ${analysis['total_holdings']:,.2f}")
                                            print("-"*60 + "\n")
                
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
