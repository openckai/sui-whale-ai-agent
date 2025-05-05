from typing import List, Dict, Set, Optional
from datetime import datetime
from db.models import WhaleHolder, WhaleMovement, Token
from api_clients import BlockberryClient
import os

class WhaleService:
    def __init__(self):
        self.blockberry = BlockberryClient(api_key=os.getenv("BLOCKBERRY_API_KEY"))
        self.min_holdings = 20_000

    async def get_token_whales(self, coin_type: str) -> List[Dict]:
        """Get whale holders for a specific token"""
        holders = await self.blockberry.get_token_holders_async(coin_type)
        whales = [h for h in holders if float(h['usd_value']) >= self.min_holdings]
        return whales

    async def get_whale_addresses_for_tokens(self, trending_tokens: List[Dict]) -> Set[str]:
        """Get unique whale addresses for multiple tokens"""
        whale_addresses = set()
        for token_data in trending_tokens:
            try:
                whales = await self.get_token_whales(token_data['coin_type'])
                for whale in whales:
                    whale_addresses.add(whale['address'])
            except Exception as e:
                print(f"Error fetching holders for {token_data['symbol']}: {e}")
        return whale_addresses

    def store_whale_holder(self, db, holder_data: Dict, token: Token, detector) -> WhaleHolder:
        """Store whale holder data and track movements"""
        holder = db.query(WhaleHolder).filter_by(
            address=holder_data['address'],
            token_id=token.id
        ).first()
        
        if not holder:
            holder = WhaleHolder(
                token_id=token.id,
                address=holder_data['address'],
                balance=float(holder_data['balance']),
                usd_value=float(holder_data['usd_value']),
                percentage=float(holder_data['percentage'])
            )
            db.add(holder)
        else:
            if holder.balance != float(holder_data['balance']):
                movement = self._create_movement(holder, holder_data, token)
                if movement:
                    db.add(movement)
                    detector.update_wallet_stats(db, holder.address, movement)
                else:
                    detector.update_wallet_stats(db, holder.address)
                
                self._update_holder_data(holder, holder_data)
        
        db.commit()
        return holder

    def _create_movement(self, holder: WhaleHolder, holder_data: Dict, token: Token) -> Optional[WhaleMovement]:
        movement_type = 'buy' if float(holder_data['balance']) > holder.balance else 'sell'
        return WhaleMovement(
            token_id=token.id,
            holder_id=holder.id,
            movement_type=movement_type,
            amount=abs(float(holder_data['balance']) - holder.balance),
            usd_value=abs(float(holder_data['usd_value']) - holder.usd_value),
            timestamp=datetime.utcnow()
        )

    def _update_holder_data(self, holder: WhaleHolder, holder_data: Dict):
        holder.balance = float(holder_data['balance'])
        holder.usd_value = float(holder_data['usd_value'])
        holder.percentage = float(holder_data['percentage']) 