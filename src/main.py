import os
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import exists

from db.database import init_db, get_db
from db.models import Token, WhaleHolder, WhaleMovement, WalletStats
from api_clients import BlockberryClient, InsideXClient, DexScreenerClient
from whale_detector.detector import WhaleDetector

# Load environment variables
load_dotenv()

# Initialize API clients
blockberry = BlockberryClient(api_key=os.getenv("BLOCKBERRY_API_KEY"))
insidex = InsideXClient(api_key=os.getenv("INSIDEX_API_KEY"))
dexscreener = DexScreenerClient()

# Rate limiting settings
BLOCKBERRY_RATE_LIMIT = 20  # seconds between calls

def sleep_between_calls():
    """Sleep between Blockberry API calls"""
    time.sleep(BLOCKBERRY_RATE_LIMIT)

def init_database():
    """Initialize the database tables"""
    init_db()
    print("Database initialized successfully")

def get_trending_tokens(min_market_cap: float = 1_000_000) -> List[Dict]:
    """
    Get trending tokens with minimum market cap
    
    Args:
        min_market_cap: Minimum market cap in USD
    """
    tokens = insidex.get_trending_tokens(min_market_cap=min_market_cap)
    print(f"\nFound {len(tokens)} trending tokens with >${min_market_cap:,} market cap")
    for token in tokens[:5]:  # Show top 5
        print(f"\nToken: {token['symbol']}")
        print(f"Market Cap: ${token['market_cap']:,.2f}")
        print(f"Price: ${token['price']:,.6f}")
        print(f"24h Volume: ${token['volume_24h']:,.2f}")
    return tokens

def get_token_whales(coin_type: str, min_holdings: float = 20_000) -> List[Dict]:
    """
    Get whale holders for a specific token
    
    Args:
        coin_type: Token coin type (e.g., "0x2::sui::SUI")
        min_holdings: Minimum USD value to be considered a whale
    """
    print(f"\nFetching holders for {coin_type}...")
    holders = blockberry.get_token_holders(coin_type)
    whales = [h for h in holders if float(h['usd_value']) >= min_holdings]
    
    print(f"Found {len(whales)} whales holding >${min_holdings:,} for {coin_type}")
    for whale in whales[:5]:  # Show top 5
        print(f"\nAddress: {whale['address']}")
        print(f"Holdings: ${float(whale['usd_value']):,.2f}")
        print(f"Percentage: {float(whale['percentage']):,.2f}%")
    return whales

async def get_token_whales_batch(coin_types: List[str], min_holdings: float = 20_000) -> Dict[str, List[Dict]]:
    """
    Get whale holders for multiple tokens with rate limiting
    
    Args:
        coin_types: List of token coin types
        min_holdings: Minimum USD value to be considered a whale
    """
    results = {}
    for coin_type in coin_types:
        try:
            results[coin_type] = get_token_whales(coin_type, min_holdings)
            if coin_type != coin_types[-1]:  # Don't sleep after the last call
                print(f"Waiting {BLOCKBERRY_RATE_LIMIT} seconds before next API call...")
                await asyncio.sleep(BLOCKBERRY_RATE_LIMIT)
        except Exception as e:
            print(f"Error fetching whales for {coin_type}: {e}")
            results[coin_type] = []
    return results

def get_wallet_stats(address: str) -> Dict:
    """
    Get detailed statistics for a wallet address
    
    Args:
        address: Wallet address to analyze
    """
    with get_db() as db:
        stats = db.query(WalletStats).filter_by(address=address).first()
        if not stats:
            print(f"No statistics found for wallet {address}")
            return {}
        
        movements = db.query(WhaleMovement).join(WhaleHolder).filter(
            WhaleHolder.address == address
        ).order_by(WhaleMovement.timestamp.desc()).all()
        
        holdings = db.query(WhaleHolder).filter_by(address=address).all()
        
        result = {
            "address": address,
            "total_volume_usd": stats.total_volume_usd,
            "total_trades": stats.total_trades,
            "win_rate": stats.win_rate(),
            "total_pnl_usd": stats.total_pnl_usd,
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
                    "usd_value": m.usd_value,
                    "timestamp": m.timestamp
                }
                for m in movements[:5]  # Last 5 movements
            ]
        }
        
        print(f"\nWallet Statistics for {address}:")
        print(f"Total Volume: ${result['total_volume_usd']:,.2f}")
        print(f"Total Trades: {result['total_trades']}")
        print(f"Win Rate: {result['win_rate']:.1f}%")
        print(f"Total PnL: ${result['total_pnl_usd']:,.2f}")
        
        print("\nCurrent Holdings:")
        for holding in result['current_holdings']:
            print(f"{holding['token']}: ${holding['usd_value']:,.2f} ({holding['percentage']:.2f}%)")
        
        print("\nRecent Movements:")
        for move in result['recent_movements']:
            print(f"{move['timestamp']}: {move['type']} {move['token']} ${move['usd_value']:,.2f}")
        
        return result

def start_whale_monitoring(
    min_market_cap: float = 1_000_000,
    min_whale_holdings: float = 20_000,
    update_interval: int = 300
):
    """
    Start the whale monitoring system
    
    Args:
        min_market_cap: Minimum market cap for monitored tokens
        min_whale_holdings: Minimum USD value to be considered a whale
        update_interval: Update interval in seconds
    """
    detector = WhaleDetector(
        min_market_cap=min_market_cap,
        min_whale_holdings=min_whale_holdings,
        update_interval=update_interval
    )
    
    print("\nStarting Whale Detector:")
    print(f"Minimum Market Cap: ${min_market_cap:,}")
    print(f"Minimum Whale Holdings: ${min_whale_holdings:,}")
    print(f"Update Interval: {update_interval} seconds")
    
    detector.start()

def get_token_pair_info(pair_id: str) -> Dict:
    """
    Get detailed information about a token pair
    
    Args:
        pair_id: DEX Screener pair ID
    """
    pair_data = dexscreener.get_token_pair_data(pair_id)
    
    print(f"\nPair Information:")
    print(f"Base Token: {pair_data['base_token']['symbol']}")
    print(f"Quote Token: {pair_data['quote_token']['symbol']}")
    print(f"Price USD: ${pair_data['price_usd']:,.6f}")
    print(f"24h Volume: ${pair_data['volume_24h']:,.2f}")
    print(f"Liquidity USD: ${pair_data['liquidity_usd']:,.2f}")
    
    return pair_data

def analyze_token_distribution(coin_type: str, min_holdings: float = 1000) -> Dict:
    """
    Analyze token holder distribution
    
    Args:
        coin_type: Token coin type
        min_holdings: Minimum USD value to include
    """
    print(f"\nFetching holders for distribution analysis...")
    holders = blockberry.get_token_holders(coin_type)
    print(f"Found {len(holders)} holders for {coin_type}")
    
    # Filter and categorize holders
    whales = []
    medium_holders = []
    small_holders = []
    
    for holder in holders:
        usd_value = float(holder['usd_value'])
        if usd_value >= 20_000:
            whales.append(holder)
        elif usd_value >= 5_000:
            medium_holders.append(holder)
        elif usd_value >= min_holdings:
            small_holders.append(holder)
    
    # Calculate statistics
    total_holders = len(whales) + len(medium_holders) + len(small_holders)
    whale_value = sum(float(h['usd_value']) for h in whales)
    medium_value = sum(float(h['usd_value']) for h in medium_holders)
    small_value = sum(float(h['usd_value']) for h in small_holders)
    total_value = whale_value + medium_value + small_value
    
    result = {
        "total_holders": total_holders,
        "distribution": {
            "whales": {
                "count": len(whales),
                "total_value": whale_value,
                "percentage": (whale_value / total_value * 100) if total_value > 0 else 0
            },
            "medium": {
                "count": len(medium_holders),
                "total_value": medium_value,
                "percentage": (medium_value / total_value * 100) if total_value > 0 else 0
            },
            "small": {
                "count": len(small_holders),
                "total_value": small_value,
                "percentage": (small_value / total_value * 100) if total_value > 0 else 0
            }
        }
    }
    
    print(f"\nToken Distribution Analysis for {coin_type}:")
    print(f"Total Holders: {total_holders}")
    print("\nWhales (>${:,.0f}):".format(20_000))
    print(f"Count: {result['distribution']['whales']['count']}")
    print(f"Total Value: ${result['distribution']['whales']['total_value']:,.2f}")
    print(f"Percentage: {result['distribution']['whales']['percentage']:.1f}%")
    
    print("\nMedium Holders (>${:,.0f}-${:,.0f}):".format(5_000, 20_000))
    print(f"Count: {result['distribution']['medium']['count']}")
    print(f"Total Value: ${result['distribution']['medium']['total_value']:,.2f}")
    print(f"Percentage: {result['distribution']['medium']['percentage']:.1f}%")
    
    print("\nSmall Holders (>${:,.0f}-${:,.0f}):".format(min_holdings, 5_000))
    print(f"Count: {result['distribution']['small']['count']}")
    print(f"Total Value: ${result['distribution']['small']['total_value']:,.2f}")
    print(f"Percentage: {result['distribution']['small']['percentage']:.1f}%")
    
    return result

async def analyze_multiple_tokens(coin_types: List[str]) -> Dict[str, Dict]:
    """
    Analyze multiple tokens with rate limiting
    
    Args:
        coin_types: List of token coin types to analyze
    """
    results = {}
    for coin_type in coin_types:
        try:
            print(f"\nAnalyzing {coin_type}...")
            results[coin_type] = analyze_token_distribution(coin_type)
            if coin_type != coin_types[-1]:  # Don't sleep after the last call
                print(f"Waiting {BLOCKBERRY_RATE_LIMIT} seconds before next analysis...")
                await asyncio.sleep(BLOCKBERRY_RATE_LIMIT)
        except Exception as e:
            print(f"Error analyzing {coin_type}: {e}")
            results[coin_type] = None
    return results

def store_token(db, token_data: Dict) -> Token:
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

def store_whale_holder(db, holder_data: Dict, token: Token) -> WhaleHolder:
    """Store whale holder data in database"""
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
        # If balance changed, create movement record
        if holder.balance != float(holder_data['balance']):
            movement_type = 'buy' if float(holder_data['balance']) > holder.balance else 'sell'
            movement = WhaleMovement(
                token_id=token.id,
                holder_id=holder.id,
                movement_type=movement_type,
                amount=abs(float(holder_data['balance']) - holder.balance),
                usd_value=abs(float(holder_data['usd_value']) - holder.usd_value),
                timestamp=datetime.utcnow()
            )
            db.add(movement)
        
        # Update holder data
        holder.balance = float(holder_data['balance'])
        holder.usd_value = float(holder_data['usd_value'])
        holder.percentage = float(holder_data['percentage'])
    
    db.commit()
    return holder

def update_wallet_statistics(db, address: str, movement: Optional[WhaleMovement] = None):
    """Update wallet statistics based on movements"""
    stats = db.query(WalletStats).filter_by(address=address).first()
    
    if not stats:
        stats = WalletStats(
            address=address,
            total_volume_usd=0,
            total_trades=0,
            total_pnl_usd=0
        )
        db.add(stats)
    
    if movement:
        stats.total_volume_usd += movement.usd_value
        stats.total_trades += 1
        # Simple PnL calculation - can be enhanced based on requirements
        if movement.movement_type == 'sell':
            stats.total_pnl_usd += movement.usd_value
        
    db.commit()
    return stats

async def main_async():
    """Async main function for batch processing with database storage"""
    # Initialize database
    init_database()
    
    # Get trending tokens
    trending = get_trending_tokens(min_market_cap=1_000_000)
    
    if trending:
        with get_db() as db:
            # Store trending tokens and get coin types
            coin_types = []
            for token_data in trending[:1]:  # Process top 5 tokens
                token = store_token(db, token_data)
                coin_types.append(token_data['coin_type'])
                print(f"\nStored/Updated token: {token.symbol}")
        
            # Analyze multiple tokens
            print("\nAnalyzing multiple tokens...")
            analysis_results = await analyze_multiple_tokens(coin_types)
            
            # Get whales for multiple tokens
            print("\nGetting whales for multiple tokens...")
            whale_results = await get_token_whales_batch(coin_types)
            
            # Process results and store data
            for coin_type in coin_types:
                print(f"\nProcessing results for {coin_type}:")
                
                # Get token from database
                token = db.query(Token).filter_by(coin_type=coin_type).first()
                if not token:
                    print(f"Token not found in database: {coin_type}")
                    continue
                
                if coin_type in whale_results and whale_results[coin_type]:
                    whales = whale_results[coin_type]
                    print(f"Storing {len(whales)} whale holders...")
                    
                    for whale_data in whales:
                        # Store whale holder
                        holder = store_whale_holder(db, whale_data, token)
                        
                        # Update wallet statistics
                        update_wallet_statistics(db, holder.address)
                    
                    print(f"Successfully stored whale data for {token.symbol}")
                
                if coin_type in analysis_results and analysis_results[coin_type]:
                    print("Distribution analysis data stored")
            
            print("\nDatabase update completed successfully")

if __name__ == "__main__":
    # Run async main
    asyncio.run(main_async())