from typing import Dict, List, Optional
from .base_client import BaseAPIClient, APIError, APIMissingDataError
import logging

logger = logging.getLogger(__name__)

class DexScreenerClient(BaseAPIClient):
    def __init__(self):
        super().__init__(
            base_url="https://api.dexscreener.com",
            api_key=None,  # DEX Screener doesn't require an API key
            timeout=30.0
        )

    def get_token_pair_data(self, pair_url_id: str) -> Dict:
        """
        Get detailed data for a specific token pair
        
        Args:
            pair_url_id: The token pair identifier (e.g., "sui/0x123...")
            
        Returns:
            Dictionary containing pair data including price, volume, etc.
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If pair data is not found or invalid
        """
        try:
            response = self.get(f"latest/dex/pairs/{pair_url_id}")
            
            if not response or 'pair' not in response:
                raise APIMissingDataError(f"Pair data not found for: {pair_url_id}")
                
            pair = response.get("pair", {})
            
            # Validate required fields
            if not pair.get("pairAddress"):
                raise APIMissingDataError(f"Missing pair address for: {pair_url_id}")
                
            try:
                return {
                    "pair_address": pair.get("pairAddress"),
                    "base_token": {
                        "address": pair.get("baseToken", {}).get("address"),
                        "name": pair.get("baseToken", {}).get("name"),
                        "symbol": pair.get("baseToken", {}).get("symbol")
                    },
                    "quote_token": {
                        "address": pair.get("quoteToken", {}).get("address"),
                        "name": pair.get("quoteToken", {}).get("name"),
                        "symbol": pair.get("quoteToken", {}).get("symbol")
                    },
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "price_native": float(pair.get("priceNative", 0)),
                    "volume_24h": float(pair.get("volume24h", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "price_change": {
                        "5m": float(pair.get("priceChange", {}).get("m5", 0)),
                        "1h": float(pair.get("priceChange", {}).get("h1", 0)),
                        "24h": float(pair.get("priceChange", {}).get("h24", 0))
                    },
                    "fdv": float(pair.get("fdv", 0)),
                    "market_cap": float(pair.get("marketCap", 0))
                }
            except (ValueError, TypeError) as e:
                raise APIMissingDataError(f"Invalid numeric data in pair response: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error fetching pair data for {pair_url_id}: {e}")
            raise APIError(f"Failed to get pair data: {str(e)}")

    def get_latest_token_profiles(self) -> List[Dict]:
        """
        Get the latest token profiles
        
        Returns:
            List of token profiles with their metadata
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If response format is invalid
        """
        try:
            response = self.get("token-profiles/latest/v1")
            
            if not isinstance(response, list):
                raise APIMissingDataError("Expected list response from token profiles endpoint")
                
            profiles = []
            for profile in response:
                try:
                    # Validate required fields
                    if not profile.get("tokenAddress") or not profile.get("chainId"):
                        logger.warning(f"Skipping profile with missing required fields: {profile}")
                        continue
                        
                    profiles.append({
                        "chain_id": profile.get("chainId"),
                        "token_address": profile.get("tokenAddress"),
                        "url": profile.get("url"),
                        "icon": profile.get("icon"),
                        "header": profile.get("header"),
                        "description": profile.get("description"),
                        "links": profile.get("links", [])
                    })
                except Exception as e:
                    logger.warning(f"Error processing token profile: {e}")
                    continue
                    
            return profiles
            
        except Exception as e:
            logger.error(f"Error fetching latest token profiles: {e}")
            raise APIError(f"Failed to get token profiles: {str(e)}")

    def search_pairs(self, query: str) -> List[Dict]:
        """
        Search for token pairs
        
        Args:
            query: Search query (token name, symbol, or address)
            
        Returns:
            List of matching pairs
            
        Raises:
            APIError: If there is an error fetching data
            APIMissingDataError: If response format is invalid
        """
        try:
            response = self.get(f"latest/dex/search/?q={self.encode_url_component(query)}")
            
            if not isinstance(response, dict) or 'pairs' not in response:
                raise APIMissingDataError("Invalid response format from search endpoint")
                
            pairs = response.get("pairs", [])
            result_pairs = []
            
            for pair in pairs:
                try:
                    # Validate required fields
                    if not pair.get("pairAddress"):
                        logger.warning(f"Skipping pair with missing address: {pair}")
                        continue
                        
                    result_pairs.append({
                        "pair_address": pair.get("pairAddress"),
                        "dex_id": pair.get("dexId"),
                        "chain_id": pair.get("chainId"),
                        "base_token": {
                            "address": pair.get("baseToken", {}).get("address"),
                            "name": pair.get("baseToken", {}).get("name"),
                            "symbol": pair.get("baseToken", {}).get("symbol")
                        },
                        "quote_token": {
                            "address": pair.get("quoteToken", {}).get("address"),
                            "name": pair.get("quoteToken", {}).get("name"),
                            "symbol": pair.get("quoteToken", {}).get("symbol")
                        },
                        "price_usd": float(pair.get("priceUsd", 0)),
                        "volume_24h": float(pair.get("volume24h", 0)),
                        "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0))
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing pair data: {e}")
                    continue
                    
            return result_pairs
            
        except Exception as e:
            logger.error(f"Error searching pairs with query '{query}': {e}")
            raise APIError(f"Failed to search pairs: {str(e)}") 