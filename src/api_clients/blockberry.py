import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .base_client import BaseAPIClient

class BlockberryClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api.blockberry.one",
            api_key=api_key,
            timeout=120.0
        )

    async def get_token_holders_async(self, 
                              coin_type: str, 
                              page: int = 0, 
                              size: int = 20, 
                              order_by: str = "DESC", 
                              sort_by: str = "AMOUNT") -> List[Dict]:
        """
        Get top holders for a given coin type (async version)
        """
        encoded_coin_type = self.encode_url_component(coin_type)
        
        params = {
            "page": page,
            "size": size,
            "orderBy": order_by,
            "sortBy": sort_by
        }
        
        endpoint = f"sui/v1/coins/{encoded_coin_type}/holders"
        print(f"Fetching holders for {coin_type} from {endpoint}")
        response = await self.get_async(endpoint, params)
        
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

    async def get_top_accounts_async(self, 
                             page: int = 0, 
                             size: int = 20, 
                             order_by: str = "DESC", 
                             sort_by: str = "BALANCE") -> List[Dict]:
        """
        Get top SUI accounts by balance (async version)
        """
        params = {
            "page": page,
            "size": size,
            "orderBy": order_by,
            "sortBy": sort_by
        }
        
        response = await self.get_async("sui/v1/accounts", params)
        accounts = response.get("content", [])
        
        return [
            {
                "address": account.get("address"),
                "balance": account.get("balance"),
                "usd_value": account.get("usdValue")
            }
            for account in accounts
        ]

    async def get_whale_holders_async(self, 
                              coin_type: str, 
                              min_usd_value: float = 50000.0, 
                              exclude_exchanges: bool = True,
                              **kwargs) -> List[Dict]:
        """
        Get whale holders for a given coin type with minimum USD value (async version)
        """
        holders = await self.get_token_holders_async(coin_type, **kwargs)
        
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

    async def get_token_details_async(self, coin_type: str, timeout: int = 60, max_retries: int = 3) -> Dict:
        """
        Get details for a given coin type (async version)
        """
        encoded_coin_type = self.encode_url_component(coin_type)
        endpoint = f"sui/v1/coins/{encoded_coin_type}"
        print(f"Fetching details for {coin_type} from {endpoint}")
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(20)  # Sleep for 20 seconds between API calls
                response = await self.get_async(endpoint)
                print(f"Response: {response}")
                
                if not response:
                    return None

                token_details = {
                    'symbol': response.get('coinSymbol', ''),
                    'name': response.get('coinName', ''),
                    'market_cap': float(response.get('marketCap') or 0),
                    'price': float(response.get('price') or 0),
                    'volume_24h': float(response.get('totalVolume') or 0),
                    'holders': int(response.get('holdersCount') or 0)
                }
                
                return token_details
                
            except TimeoutError:
                print(f"Request timed out, attempt {attempt + 1} of {max_retries}")
                if attempt == max_retries - 1:
                    print(f"Max retries ({max_retries}) reached, giving up")
                    return None
                    
            except Exception as e:
                print(f"Error fetching token details: {str(e)}")
                return None

    # Keep synchronous methods for backward compatibility
    def get_token_holders(self, coin_type: str, **kwargs) -> List[Dict]:
        """Synchronous version of get_token_holders_async"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_token_holders_async(coin_type, **kwargs))

    def get_top_accounts(self, **kwargs) -> List[Dict]:
        """Synchronous version of get_top_accounts_async"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_top_accounts_async(**kwargs))

    def get_whale_holders(self, coin_type: str, **kwargs) -> List[Dict]:
        """Synchronous version of get_whale_holders_async"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_whale_holders_async(coin_type, **kwargs))

    def get_token_details(self, coin_type: str, **kwargs) -> Dict:
        """Synchronous version of get_token_details_async"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_token_details_async(coin_type, **kwargs))
    async def get_wallet_holdings_async(self, address: str) -> List[Dict]:
        """Get wallet holdings for a given address"""
        encoded_address = self.encode_url_component(address)
        endpoint = f"sui/v1/accounts/{encoded_address}/objects"
        
        try:
            await asyncio.sleep(20)  # Sleep for 20 seconds between API calls
            print(f"Fetching holdings for {address} from {endpoint} and waiting 20 seconds")
            response = await self.post_async(endpoint, json={"objectTypes": ["coin"]})
            if not response:
                return []
            
            holdings = response.get("coins", []) or []
            results = []
            
            for holding in holdings:
                coin_type = holding.get("coinType")
                if not coin_type:
                    continue
                try:
                    # Extract values with proper defaults based on API response format
                    balance = float(holding.get("totalBalance", 0))
                    coin_price = float(holding.get("coinPrice", 0))
                    usd_value = balance * coin_price
                    
                    results.append({
                        "coin_type": coin_type,
                        "symbol": holding.get("coinSymbol", "UNKNOWN"),
                        "name": holding.get("coinName", "UNKNOWN"), 
                        "balance": balance,
                        "usd_value": usd_value,
                        "price": coin_price,
                        "decimals": holding.get("decimals", 9),
                        "objects_count": holding.get("objectsCount", 0),
                        "verified": holding.get("verified", False),
                        "bridged": holding.get("bridged", False),
                        "img_url": holding.get("imgUrl"),
                        "security_message": holding.get("securityMessage"),
                        "has_no_metadata": holding.get("hasNoMetadata", False)
                    })
                    
                except (ValueError, TypeError) as e:
                    print(f"Error parsing holding data for {coin_type}: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"Error fetching wallet holdings for {address}: {e}")
            return []

    async def get_coin_metadata(self, coin_type: str) -> Dict:
        """Get metadata for a given coin type"""
        if coin_type in self.coin_metadata_cache:
            return self.coin_metadata_cache[coin_type]
            
        encoded_coin_type = self.encode_url_component(coin_type)
        endpoint = f"sui/v1/coins/{encoded_coin_type}"
        
        try:
            await asyncio.sleep(20)  # Sleep for 20 seconds between API calls
            response = await self.get_async(endpoint)
            if not response:
                return {}
                
            metadata = {
                "symbol": response.get("coinSymbol", ""),
                "name": response.get("coinName", ""),
                "decimals": response.get("decimals", 9),
                "price": float(response.get("price") or 0),
                "market_cap": float(response.get("marketCap") or 0),
                "volume_24h": float(response.get("totalVolume") or 0)
            }
            
            self.coin_metadata_cache[coin_type] = metadata
            return metadata
            
        except Exception as e:
            print(f"Error fetching metadata for {coin_type}: {e}")
            return {}
        
    async def fetch_whale_activity(self, address: str, since_minutes: int = 1440) -> List[Dict]:
        """
        Fetch recent activity for a whale address
        
        Args:
            address: The wallet address to get activity for
            since_minutes: Only return activities within this many minutes (default 24 hours)
            
        Returns:
            List of recent activities
        """
        endpoint = f"sui/v1/accounts/{address}/activity"
        params = {
            "size": 20,
            "orderBy": "DESC"
        }
        print(f"Fetching activity for {address} from {endpoint} with params {params}")
        
        try:
            await asyncio.sleep(30)  # Sleep for 20 seconds between API calls
            print(f"Fetching activity for {address} from {endpoint} with params {params} and waiting 30 seconds")
            response = await self.get_async(endpoint, params=params)
            if not response:
                return []
                
            data = response.get("content", [])
            
            # Filter for activities within the last `since_minutes`
            now = datetime.utcnow()
            recent = []
            
            for activity in data:
                timestamp = activity.get("timestamp")
                if timestamp:
                    activity_time = datetime.utcfromtimestamp(timestamp / 1000)
                    if now - activity_time <= timedelta(minutes=since_minutes):
                        recent.append(activity)
                        
            return recent
            
        except Exception as e:
            print(f"Error fetching activity for {address}: {e}")
            return []
