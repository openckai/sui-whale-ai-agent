from typing import Dict, List, Optional
from numbers import Number
from .base_client import BaseAPIClient, APIError, APIMissingDataError
import logging

logger = logging.getLogger(__name__)

class InsideXClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api-ex.insidex.trade",
            api_key=api_key,
            timeout=30.0
        )

    def get_trending_tokens(self, min_market_cap: Optional[float] = None, network: str = "sui") -> List[Dict]:
        """
        Get trending tokens with optional market cap filter and network filter
        
        Args:
            min_market_cap: Minimum market cap in USD to filter tokens
            network: Network to filter tokens by (default "sui")
            
        Returns:
            List of trending tokens with their details
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If response data is invalid
        """
        try:
            response = self.get("coins/trending")
            
            if not isinstance(response, list):
                raise APIMissingDataError("Expected list response from trending tokens endpoint")
                
            tokens = response
            
            # Filter by network and market cap if specified
            filtered_tokens = []
            for token in tokens:
                try:
                    coin_type = token.get('coin', '')
                    # Check if token is from specified network
                    if not coin_type.startswith(f"0x"):  # Non-Sui tokens don't start with 0x
                        continue
                        
                    if min_market_cap is not None:
                        try:
                            market_cap = float(token.get('marketCap', 0))
                            if market_cap < min_market_cap:
                                continue
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid market cap value for token {coin_type}")
                            continue
                            
                    # Clean and standardize the response
                    cleaned_token = self._clean_token_data(token)
                    if cleaned_token:
                        filtered_tokens.append(cleaned_token)
                        
                except Exception as e:
                    logger.warning(f"Error processing token data: {e}")
                    continue
            
            return filtered_tokens
            
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            raise APIError(f"Failed to get trending tokens: {str(e)}")

    def _clean_token_data(self, token: Dict) -> Optional[Dict]:
        """Clean and validate token data"""
        try:
            return {
                "symbol": token.get("coinMetadata", {}).get("symbol"),
                "name": token.get("coinMetadata", {}).get("name"),
                "coin_type": token.get("coin"),
                "market_cap": float(token.get("marketCap", 0)),
                "price": float(token.get("coinPrice", 0)),
                "volume_24h": float(token.get("volume24h", 0)),
                "price_change_24h": float(token.get("percentagePriceChange24h", 0)),
                "total_supply": token.get("coinSupply"),
                "description": token.get("coinMetadata", {}).get("description"),
                "icon_url": token.get("coinMetadata", {}).get("iconUrl"),
                "top_10_holders_percentage": float(token.get("top10HolderPercentage", 0)),
                "top_20_holders_percentage": float(token.get("top20HolderPercentage", 0)),
                "liquidity_usd": float(token.get("totalLiquidityUsd", 0)),
                "is_mintable": token.get("isMintable") == "true",
                "is_honeypot": token.get("isCoinHoneyPot") == "true",
                "suspicious_activities": token.get("suspiciousActivities", [])
            }
        except (ValueError, TypeError) as e:
            logger.warning(f"Error cleaning token data: {e}")
            return None

    def get_token_details(self, coin_type: str) -> Dict:
        """
        Get detailed information for a specific token
        
        Args:
            coin_type: The coin type (e.g., "0x2::sui::SUI")
            
        Returns:
            Detailed token information
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If token is not found or data is invalid
        """
        try:
            encoded_coin_type = self.encode_url_component(coin_type)
            response = self.get(f"coins/{encoded_coin_type}")
            
            if not response:
                raise APIMissingDataError(f"Token not found: {coin_type}")
                
            cleaned_data = self._clean_token_data(response)
            if not cleaned_data:
                raise APIMissingDataError(f"Invalid data for token: {coin_type}")
                
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Error fetching token details for {coin_type}: {e}")
            raise APIError(f"Failed to get token details: {str(e)}")

    def get_whale_holders(self, coin_type: str, min_usd_value: float = 20000) -> List[Dict]:
        """
        Get token holders with holdings value above specified USD threshold
        
        Args:
            coin_type: The coin type to get holders for
            min_usd_value: Minimum USD value of holdings to be considered (default $20k)
            
        Returns:
            List of holder data containing address and holdings value
            
        Raises:
            APIError: If there is an error fetching data
        """
        try:
            endpoint = f"coins/{coin_type}/holders"
            response = self.get(endpoint)
            
            if not isinstance(response, dict) or 'holders' not in response:
                raise APIMissingDataError("Invalid response format from holders endpoint")
                
            holders = response.get("holders", [])
            
            # Filter and clean holder data
            whale_holders = []
            for holder in holders:
                try:
                    holdings_value = float(holder.get("holdingsValue", 0))
                    if holdings_value >= min_usd_value:
                        whale_holders.append({
                            "address": holder.get("address"),
                            "holdings_value": holdings_value,
                            "token_amount": float(holder.get("tokenAmount", 0))
                        })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid holder data: {e}")
                    continue
            
            return sorted(whale_holders, key=lambda x: x["holdings_value"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error fetching whale holders for {coin_type}: {e}")
            raise APIError(f"Failed to get whale holders: {str(e)}")
    
    def get_trader_stats(self, address: str) -> Dict:
        """
        Get trading statistics for a wallet address
        
        Args:
            address: The wallet address to get stats for
            
        Returns:
            Dict containing trading metrics like PnL, volume, win rate etc.
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If trader data is not found
        """
        try:
            endpoint = f"spot-portfolio/{address}/spot-trade-stats"
            response = self.get(endpoint)
            
            if not response:
                raise APIMissingDataError(f"No trading stats found for address: {address}")
            
            # Clean and validate the response data
            try:
                return {
                    "address": response.get("user"),
                    "is_bot": response.get("isBot", False),
                    "last_trade_timestamp": response.get("lastTradeTimestamp"),
                    "pnl": float(response.get("pnl") or 0),
                    "total_trades": int(response.get("totalTrades") or 0), 
                    "volume": float(response.get("volume") or 0),
                    "avg_sold_in": float(response["avgSoldIn"]) if isinstance(response.get("avgSoldIn"), Number) else None,
                    "gain": float(response.get("gain") or 0),
                    "invested": float(response.get("invested") or 0),
                    "losses": int(response.get("loses") or 0),
                    "loss_amount": float(response.get("loss") or 0),
                    "roi": float(response.get("roi") or 0),
                    "win_rate": float(response.get("winRate") * 100 or 0),
                    "wins": int(response.get("wins") or 0)
                }
            except (ValueError, TypeError) as e:
                raise APIMissingDataError(f"Invalid trading stats data: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error fetching trader stats for {address}: {e}")
            raise APIError(f"Failed to get trader stats: {str(e)}")


