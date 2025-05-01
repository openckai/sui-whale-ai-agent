from typing import Dict, List, Optional
from .base_client import BaseAPIClient

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
        """
        response = self.get("coins/trending")
        tokens = response if isinstance(response, list) else []
        
        # Filter by network and market cap if specified
        filtered_tokens = []
        for token in tokens:
            coin_type = token.get('coin', '')
            # Check if token is from specified network
            if not coin_type.startswith(f"0x"):  # Non-Sui tokens don't start with 0x
                continue
                
            if min_market_cap is not None:
                if float(token.get('marketCap', 0)) < min_market_cap:
                    continue
                    
            filtered_tokens.append(token)
        
        # Clean and standardize the response
        return [
            {
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
            for token in filtered_tokens
        ]

    def get_token_details(self, coin_type: str) -> Dict:
        """
        Get detailed information for a specific token
        
        Args:
            coin_type: The coin type (e.g., "0x2::sui::SUI")
            
        Returns:
            Detailed token information
        """
        encoded_coin_type = self.encode_url_component(coin_type)
        response = self.get(f"coins/{encoded_coin_type}")
        
        if not response:
            raise Exception(f"Token not found: {coin_type}")
            
        return {
            "symbol": response.get("coinMetadata", {}).get("symbol"),
            "name": response.get("coinMetadata", {}).get("name"),
            "coin_type": response.get("coin"),
            "market_cap": float(response.get("marketCap", 0)),
            "price": float(response.get("coinPrice", 0)),
            "volume_24h": float(response.get("volume24h", 0)),
            "price_change_24h": float(response.get("percentagePriceChange24h", 0)),
            "total_supply": response.get("coinSupply"),
            "description": response.get("coinMetadata", {}).get("description"),
            "icon_url": response.get("coinMetadata", {}).get("iconUrl"),
            "top_10_holders_percentage": float(response.get("top10HolderPercentage", 0)),
            "top_20_holders_percentage": float(response.get("top20HolderPercentage", 0)),
            "liquidity_usd": float(response.get("totalLiquidityUsd", 0)),
            "is_mintable": response.get("isMintable") == "true",
            "is_honeypot": response.get("isCoinHoneyPot") == "true",
            "suspicious_activities": response.get("suspiciousActivities", [])
        }

    def get_whale_holders(self, coin_type: str, min_usd_value: float = 20000) -> List[Dict]:
        """
        Get token holders with holdings value above specified USD threshold
        
        Args:
            coin_type: The coin type to get holders for
            min_usd_value: Minimum USD value of holdings to be considered (default $20k)
            
        Returns:
            List of holder data containing address and holdings value
        """
        endpoint = f"coins/{coin_type}/holders"
        response = self.get(endpoint)
        holders = response.get("holders", [])

        # Filter holders by USD value threshold
        whale_holders = [
            {
                "address": holder.get("address"),
                "holdings_value": float(holder.get("holdingsValue", 0)),
                "token_amount": float(holder.get("tokenAmount", 0))
            }
            for holder in holders
            if float(holder.get("holdingsValue", 0)) >= min_usd_value
        ]

        return sorted(whale_holders, key=lambda x: x["holdings_value"], reverse=True)