import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API keys
BLOCKBERRY_API_KEY = os.getenv("BLOCKBERRY_API_KEY")
INSIDEX_API_KEY = os.getenv("INSIDEX_API_KEY")

# Constants
MIN_MARKET_CAP = 1000000  # $1M
MIN_HOLDER_USD_VALUE = 50000  # $50K

def sleep(seconds):
    """Sleep function for rate limiting"""
    time.sleep(seconds)

def test_blockberry_api():
    """Test Blockberry API endpoints"""
    try:
        # Test accounts endpoint
        url = "https://api.blockberry.one/sui/v1/coins?page=0&size=20&orderBy=DESC&sortBy=AGE&withImage=TRUE"
        headers = {
            "accept": "*/*",
            "x-api-key": BLOCKBERRY_API_KEY
        }
        
        print("\nTesting Blockberry Accounts API...")
        resp = requests.get(url, headers=headers)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total Accounts: {len(data.get('content', []))}")
            # print("\nSample Account Data:")
            # for account in data.get('content', [])[:2]:  # Show first 2 accounts
            #     print(f"Address: {account.get('address')}")
            #     print(f"Balance: {account.get('balance')}")
            #     print(f"USD Value: {account.get('usdValue')}")
            #     print("---")
        else:
            print("Error Response:", resp.text)

    except Exception as e:
        print(f"Error testing Blockberry API: {str(e)}")

def test_insidex_api():
    """Test InsideX API endpoints"""
    try:
        # Test trending tokens endpoint
        url = "https://api-ex.insidex.trade/coins/trending"
        headers = {"x-api-key": INSIDEX_API_KEY}
        
        resp = requests.get(url, headers=headers)
        print("\nInsideX Trending Tokens Test:")
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total Trending Tokens: {len(data)}")
            # Filter by market cap
            high_market_cap_tokens = [token for token in data 
                                    if float(token.get('marketCap', 0)) > MIN_MARKET_CAP]
            print(f"Tokens with market cap > ${MIN_MARKET_CAP:,}: {len(high_market_cap_tokens)}")
            print("Sample Token Data:", high_market_cap_tokens[:1] if high_market_cap_tokens else "None")
        else:
            print("Error Response:", resp.text)

    except Exception as e:
        print(f"Error testing InsideX API: {str(e)}")

def test_dexscreener_api():
    """Test DEX Screener API for latest token profiles"""
    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        headers = {"accept": "*/*"}
        print("\nTesting DEX Screener API...")
        resp = requests.get(url, headers=headers)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Sample Token Profile:")
            if isinstance(data, list) and len(data) > 0:
                print(data[0])
            elif isinstance(data, dict):
                # Print the first item if the response is a dict with a list inside
                for v in data.values():
                    if isinstance(v, list) and len(v) > 0:
                        print(v[0])
                        break
                    else:
                        print(data)
        else:
            print("Error Response:", resp.text)
    except Exception as e:
        print(f"Error testing DEX Screener API: {str(e)}")

def main():
    """Main function to run all tests"""
    print("Starting API Tests...\n")
    
    # Test Blockberry API
    test_blockberry_api()
    
    # # Add delay between API calls
    # sleep(2)
    
    # # Test InsideX API
    # print("\nTesting InsideX API...")
    # test_insidex_api()

    # # Test DEX Screener API
    # test_dexscreener_api()

if __name__ == "__main__":
    main()
