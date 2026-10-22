from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from SmartApi import SmartConnect
import requests
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List of popular Indian stocks to track (Symbol, Token, Exchange)
STOCKS_TO_TRACK = [
    {"name": "RELIANCE", "token": "2885", "exchange": "NSE"},
    {"name": "HDFCBANK", "token": "1333", "exchange": "NSE"},
    {"name": "ICICIBANK", "token": "4963", "exchange": "NSE"},
    {"name": "TCS", "token": "11536", "exchange": "NSE"},
    {"name": "INFY", "token": "1594", "exchange": "NSE"},
    {"name": "SBIN", "token": "3045", "exchange": "NSE"},
    {"name": "ITC", "token": "1660", "exchange": "NSE"}
]

@app.get("/")
def read_root():
    return {"status": "API is running!"}

@app.get("/api/analyze")
def get_analysis():
    try:
        API_KEY = os.environ.get("API_KEY")
        CLIENT_CODE = os.environ.get("CLIENT_CODE")
        MPIN = os.environ.get("MPIN")
        TOTP_SECRET = os.environ.get("TOTP_SECRET")
        DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

        # 1. Login to Angel One
        totp = pyotp.TOTP(TOTP_SECRET)
        current_otp = totp.now()
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, current_otp)
        
        if not data['status']:
            return {"error": "Angel One Login Failed"}

        # 2. Get Nifty 50 Data
        nifty_data = smartApi.ltpData("NSE", "NIFTY", "26000")
        nifty_price = nifty_data['data']['ltp']

        # 3. Get Live Stock Data (The Loop)
        bullish_stocks = []
        bearish_stocks = []

        for stock in STOCKS_TO_TRACK:
            # Get full quote to see current price and previous close
            quote = smartApi.getMarketData({
                "mode": "FULL", 
                "exchangeTokens": {stock["exchange"]: [stock["token"]]}
            })
            
            if quote['status']:
                # Extract data
                live_data = quote['data']['fetched'][0]
                current_price = live_data['ltp']
                prev_close = live_data['close']
                
                # Calculate sentiment
                if current_price > prev_close:
                    bullish_stocks.append(stock["name"])
                else:
                    bearish_stocks.append(stock["name"])

        # 4. Ask DeepSeek for AI Analysis (Nifty)
        prompt = f"The Nifty 50 current price is {nifty_price}. Act as an expert Indian stock market trader. Give me a short 2-sentence analysis of the market direction. Also mention that {len(bullish_stocks)} major stocks are bullish and {len(bearish_stocks)} are bearish."
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }
        
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        ai_reply = response.json()['choices'][0]['message']['content']

        # 5. Send EVERYTHING back to the website
        return {
            "status": "success",
            "nifty_price": nifty_price,
            "analysis": ai_reply,
            "bullish_list": bullish_stocks,
            "bearish_list": bearish_stocks
        }

    except Exception as e:
        return {"error": str(e)}
