from typing import List, Dict
from db.models import Token
from api_clients import InsideXClient
import os

class TokenService:
    def __init__(self):
        self.insidex = InsideXClient(api_key=os.getenv("INSIDEX_API_KEY"))

    def get_trending_tokens(self, min_market_cap: float = 1_000_000) -> List[Dict]:
        """Get trending tokens with minimum market cap"""
        tokens = self.insidex.get_trending_tokens(min_market_cap=min_market_cap)
        print(f"\nFound {len(tokens)} trending tokens with >${min_market_cap:,} market cap")
        return tokens[:10]

    def store_token(self, db, token_data: Dict) -> Token:
        """Store token data in database"""
        token = db.query(Token).filter_by(coin_type=token_data['coin_type']).first()
        if not token:
            token = Token(
                coin_type=token_data['coin_type'],
                symbol=token_data['symbol'],
                name=token_data.get('name', token_data['symbol']),
                market_cap=token_data['market_cap'],
                price_usd=token_data['price'],
                volume_24h=token_data['volume_24h']
            )
            db.add(token)
        else:
            token.market_cap = token_data['market_cap']
            token.price_usd = token_data['price']
            token.volume_24h = token_data['volume_24h']
        
        db.commit()
        return token 