import os
import asyncio
from dotenv import load_dotenv
from db.database import init_db, get_db
from db.models import Token
from whale_detector.detector import WhaleDetector
from modules.token_analysis.token_service import TokenService
from modules.whale_monitoring.whale_service import WhaleService
from modules.utils.activity_analyzer import ActivityAnalyzer
from modules.utils.stats_service import StatsService
from modules.whale_monitoring.alert_service import AlertService

# Load environment variables
load_dotenv()

# Initialize services
token_service = TokenService()
whale_service = WhaleService()
activity_analyzer = ActivityAnalyzer()
stats_service = StatsService()
alert_service = AlertService()

def init_database():
    """Initialize the database tables"""
    init_db()
    print("Database initialized successfully")

async def process_token_data():
    """Track whale movements on LOFI for whales holding trending tokens"""
    detector = WhaleDetector(
        min_market_cap=1_000_000,
        min_whale_holdings=20_000,
        update_interval=300
    )

    # Get trending tokens
    trending = token_service.get_trending_tokens(min_market_cap=1_000_000)
    if not trending:
        print("No trending tokens found.")
        return

    with get_db() as db:
        print("\nFetching whale holders for trending tokens...")
        
        # Get whale addresses for trending tokens
        whale_addresses = await whale_service.get_whale_addresses_for_tokens(trending)
        print(f"Found {len(whale_addresses)} unique whale addresses")
        # whale_addresses = set()
        # whale_addresses.add("0x22823c31e4bfa60d8ea3052a99af6d02d70cd820b8a0a114be30b5f21beecbf7")
        # Monitor LOFI holdings
        LOFI_COIN_TYPE = "0xf22da9a24ad027cccb5f2d496cbe91de953d363513db08a3a734d361c7c17503::LOFI::LOFI"
        
        for address in whale_addresses:
            try:
                activity_list = await whale_service.blockberry.fetch_whale_activity(address, since_minutes=1440)
                
                if not activity_list:
                    continue

                detector.update_wallet_stats(db, address)
                whale_stats = stats_service.get_wallet_stats(db, address)

                if activity_analyzer.has_recent_meme_swap(activity_list, "LOFI"):
                    for activity in activity_list:
                        if "Swap" in activity.get("activityType", []):
                            token = db.query(Token).filter_by(coin_type=LOFI_COIN_TYPE).first()
                            if not token:
                                continue
                                
                            swap_details = activity_analyzer.process_swap_activity(activity, token.price_usd)
                            if swap_details:
                                alert_service.print_whale_movement("LOFI", swap_details, whale_stats)

            except Exception as e:
                print(f"Error processing whale {address}: {e}")

async def main_async():
    """Async main function for continuous monitoring"""
    init_database()
    print("\nStarting continuous whale monitoring...")
    
    while True:
        try:
            print("\n" + "="*50)
            print("Starting new monitoring cycle")
            print("="*50)
            
            await process_token_data()
            
            print("\nWaiting 30 seconds before next cycle...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"\nError in monitoring cycle: {e}")
            print("Waiting 30 seconds before retry...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main_async())
