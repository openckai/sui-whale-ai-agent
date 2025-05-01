from typing import Dict, List, Optional
from .base_client import BaseAPIClient

class BlockberryClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api.blockberry.one",
            api_key=api_key,
            timeout=60.0
        )

    def get_token_holders(self, 
                         coin_type: str, 
                         page: int = 0, 
                         size: int = 20, 
                         order_by: str = "DESC", 
                         sort_by: str = "AMOUNT") -> List[Dict]:
        """
        Get top holders for a given coin type
        
        Args:
            coin_type: The coin type (e.g., "0x2::sui::SUI")
            page: Page number for pagination
            size: Number of results per page
            order_by: Sort order (ASC or DESC)
            sort_by: Field to sort by (e.g., AMOUNT)
            
        Returns:
            List of holder data containing address, balance, and USD value
        """
        # Encode the coin type for URL safety
        encoded_coin_type = self.encode_url_component(coin_type)
        
        params = {
            "page": page,
            "size": size,
            "orderBy": order_by,
            "sortBy": sort_by
        }
        
        endpoint = f"sui/v1/coins/{encoded_coin_type}/holders"
        print(f"Fetching holders for {coin_type} from {endpoint}")
        response = self.get(endpoint, params)
        print(f"Response: {response}")
        
        # Extract and clean holder data
        holders = response.get("content", [])
        return [
            {
                "address": holder.get("holderAddress"),
                "balance": holder.get("amount"),
                "usd_value": holder.get("usdAmount"),
                "percentage": holder.get("percentage"),
                "objects_count": holder.get("objectsCount")
            }
            for holder in holders
        ]

    def get_top_accounts(self, 
                        page: int = 0, 
                        size: int = 20, 
                        order_by: str = "DESC", 
                        sort_by: str = "BALANCE") -> List[Dict]:
        """
        Get top SUI accounts by balance
        
        Args:
            page: Page number for pagination
            size: Number of results per page
            order_by: Sort order (ASC or DESC)
            sort_by: Field to sort by (e.g., BALANCE)
            
        Returns:
            List of account data containing address, balance, and USD value
        """
        params = {
            "page": page,
            "size": size,
            "orderBy": order_by,
            "sortBy": sort_by
        }
        
        response = self.get("sui/v1/accounts", params)
        accounts = response.get("content", [])
        
        return [
            {
                "address": account.get("address"),
                "balance": account.get("balance"),
                "usd_value": account.get("usdValue")
            }
            for account in accounts
        ]

    def get_whale_holders(self, 
                         coin_type: str, 
                         min_usd_value: float = 50000.0, 
                         exclude_exchanges: bool = True,
                         **kwargs) -> List[Dict]:
        """
        Get whale holders for a given coin type with minimum USD value
        
        Args:
            coin_type: The coin type (e.g., "0x2::sui::SUI")
            min_usd_value: Minimum USD value to consider as whale
            exclude_exchanges: Whether to exclude known exchange addresses
            **kwargs: Additional arguments to pass to get_token_holders
            
        Returns:
            List of whale holders filtered by USD value
        """
        # Get all holders first
        holders = self.get_token_holders(coin_type, **kwargs)
        
        # Filter by USD value and optionally exclude exchanges
        whale_holders = []
        for holder in holders:
            usd_value = float(holder.get("usd_value", 0))
            is_exchange = holder.get("is_exchange", False)
            
            if usd_value >= min_usd_value:
                if exclude_exchanges and not is_exchange:
                    whale_holders.append(holder)
                elif not exclude_exchanges:
                    whale_holders.append(holder)
        
        return whale_holders