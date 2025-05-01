from typing import Dict, List, Optional
from .base_client import BaseAPIClient

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
        """
        response = self.get(f"latest/dex/pairs/{pair_url_id}")
        pair = response.get("pair", {})
        
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

    def get_latest_token_profiles(self) -> List[Dict]:
        """
        Get the latest token profiles
        
        Returns:
            List of token profiles with their metadata
        """
        response = self.get("token-profiles/latest/v1")
        profiles = response if isinstance(response, list) else []
        
        return [
            {
                "chain_id": profile.get("chainId"),
                "token_address": profile.get("tokenAddress"),
                "url": profile.get("url"),
                "icon": profile.get("icon"),
                "header": profile.get("header"),
                "description": profile.get("description"),
                "links": profile.get("links", [])
            }
            for profile in profiles
        ]

    def search_pairs(self, query: str) -> List[Dict]:
        """
        Search for token pairs
        
        Args:
            query: Search query (token name, symbol, or address)
            
        Returns:
            List of matching pairs
        """
        response = self.get(f"latest/dex/search/?q={self.encode_url_component(query)}")
        pairs = response.get("pairs", [])
        
        return [
            {
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
            }
            for pair in pairs
        ] 