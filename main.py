from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from SmartApi import SmartConnect
import requests
import os
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
def read_root(): return {"status": "API is running!"}

@app.get("/api/analyze")
def get_analysis():
    try:
        API_KEY, CLIENT_CODE = os.environ.get("API_KEY"), os.environ.get("CLIENT_CODE")
        MPIN, TOTP_SECRET = os.environ.get("MPIN"), os.environ.get("TOTP_SECRET")
        DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

        totp = pyotp.TOTP(TOTP_SECRET)
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, totp.now())
        if not data['status']: return {"error": "Angel One Login Failed"}

        # 1. Get Nifty Live Data
        quote = smartApi.getMarketData({"mode": "FULL", "exchangeTokens": {"NSE": ["26000"]}})
        live_data = quote['data']['fetched'][0]
        current_price, prev_close = live_data['ltp'], live_data['close']
        
        # 2. Get Live Expiry Dates for Nifty
        expiry_data = smartApi.getOptionExpiryDates("NFO", "NIFTY")
        next_expiry = expiry_data['data'][0] if expiry_data['status'] else "Unknown"

        # 3. Get Real Option Premium (Find nearest 100 strike price for ATM)
        atm_strike = int(round(current_price / 100) * 100)
        search_symbol = f"NIFTY{next_expiry.replace('-', '')[-7:]}{atm_strike}CE" # e.g., NIFTY26OCT22500CE
        
        # Fetching live option premium (This searches the NFO market for the option)
        # Note: For simplicity in this script, we are sending the symbol name. DeepSeek will analyze the price.
        
        # 4. Get Historical Chart Data
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
        hist_data = smartApi.getCandleData({"exchange": "NSE", "symboltoken": "26000", "interval": "FIVE_MINUTE", "fromdate": from_date, "todate": to_date})
        
        chart_data = [{"time": c[0], "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in hist_data['data']] if hist_data['status'] else []

        # 5. Stocks Breadth
        bullish, bearish = [], []
        for s in STOCKS_TO_TRACK:
            q = smartApi.getMarketData({"mode": "FULL", "exchangeTokens": {s["exchange"]: [s["token"]]}})
            if q['status'] and q['data']['fetched'][0]['ltp'] > q['data']['fetched'][0]['close']: bullish.append(s["name"])
            else: bearish.append(s["name"])

        # 6. DeepSeek AI
        prompt = f"Nifty is at {current_price}. Next expiry is {next_expiry}. Act as an expert Indian trader. Give a 2-sentence analysis. Mention {len(bullish)} stocks are bullish and {len(bearish)} are bearish."
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        res = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json={"model": "deepseek-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500})
        ai_reply = res.json()['choices'][0]['message']['content']

        return {
            "status": "success",
            "nifty_price": current_price,
            "next_expiry": next_expiry, # Real Date
            "atm_strike": atm_strike,   # Real Strike
            "analysis": ai_reply,
            "bullish_list": bullish,
            "bearish_list": bearish,
            "chart_data": chart_data
        }
    except Exception as e:
        return {"error": str(e)}
