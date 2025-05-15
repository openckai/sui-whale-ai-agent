from typing import List, Dict, Optional
from db.models import Token
from api_clients import InsideXClient
from api_clients.base_client import APIError, APITimeoutError, APIResponseError, APIMissingDataError
import os
import logging

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self):
        self.insidex = InsideXClient(api_key=os.getenv("INSIDEX_API_KEY"))

    def get_trending_tokens(self, min_market_cap: float = 1_000_000) -> List[Dict]:
        """
        Get trending tokens with minimum market cap
        
        Args:
            min_market_cap: Minimum market cap threshold in USD
            
        Returns:
            List of trending tokens, empty list if error occurs
            
        Raises:
            APIError: If there is an unrecoverable API error
        """
        try:
            tokens = self.insidex.get_trending_tokens(min_market_cap=min_market_cap)
            logger.info(f"Found {len(tokens)} trending tokens with >${min_market_cap:,} market cap")
            return tokens[:10]
            
        except APITimeoutError as e:
            logger.error(f"Timeout getting trending tokens: {e}")
            return []  # Return empty list on timeout
            
        except APIResponseError as e:
            if e.status_code == 429:  # Rate limit
                logger.warning(f"Rate limited when getting trending tokens: {e}")
                return []
            elif e.status_code >= 500:  # Server error
                logger.error(f"Server error getting trending tokens: {e}")
                return []
            else:
                raise  # Re-raise other response errors
                
        except APIMissingDataError as e:
            logger.error(f"Missing data in trending tokens response: {e}")
            return []
            
        except APIError as e:
            logger.error(f"Error getting trending tokens: {e}")
            raise  # Re-raise unexpected API errors

    def store_token(self, db, token_data: Dict) -> Optional[Token]:
        """
        Store token data in database
        
        Args:
            db: Database session
            token_data: Token data to store
            
        Returns:
            Stored Token object, None if error occurs
            
        Raises:
            ValueError: If required token data is missing
        """
        try:
            # Validate required fields
            required_fields = ['coin_type', 'symbol', 'market_cap', 'price', 'volume_24h']
            missing_fields = [f for f in required_fields if f not in token_data]
            if missing_fields:
                raise ValueError(f"Missing required token data: {', '.join(missing_fields)}")

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
            
            try:
                db.commit()
                logger.info(f"Successfully stored/updated token {token.symbol}")
                return token
                
            except Exception as e:
                db.rollback()
                logger.error(f"Database error storing token {token_data.get('symbol')}: {e}")
                return None
                
        except ValueError as e:
            logger.error(f"Invalid token data: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error storing token: {e}")
            return None 