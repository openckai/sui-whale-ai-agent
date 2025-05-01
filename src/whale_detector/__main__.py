import os
from dotenv import load_dotenv
from src.db.database import init_db
from src.whale_detector.detector import WhaleDetector

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize database
    init_db()
    
    # Create and start whale detector
    detector = WhaleDetector(
        min_market_cap=1_000_000,  # $1M minimum market cap
        min_whale_holdings=20_000,  # $20k minimum whale holdings
        update_interval=300  # 5 minutes
    )
    
    print("Starting whale detector...")
    print(f"Minimum market cap: ${detector.min_market_cap:,}")
    print(f"Minimum whale holdings: ${detector.min_whale_holdings:,}")
    print(f"Update interval: {detector.update_interval} seconds")
    
    detector.start()

if __name__ == "__main__":
    main() 