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

        # 1. Login
        totp = pyotp.TOTP(TOTP_SECRET)
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, totp.now())
        if not data['status']: return {"error": "Angel One Login Failed", "details": data}

        # 2. Get Nifty Live Data (Passing parameters correctly)
        nifty_quote = smartApi.ltpData("NSE", "NIFTY", "26000")
        current_price = nifty_quote['data']['ltp']
        
        # Get previous close for Nifty to calculate change
        nifty_full = smartApi.getMarketData("FULL", {"NSE": ["26000"]})
        prev_close = nifty_full['data']['fetched'][0]['close']
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        # 3. Get Historical Chart Data
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
        hist_data = smartApi.getCandleData({
            "exchange": "NSE", "symboltoken": "26000", "interval": "FIVE_MINUTE", 
            "fromdate": from_date, "todate": to_date
        })
        chart_data = [{"time": c[0], "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in hist_data['data']] if hist_data['status'] else []

        # 4. Get Live Stock Data (Fixing the exchangeTokens format)
        tokens = [s["token"] for s in STOCKS_TO_TRACK]
        quote_data = smartApi.getMarketData("FULL", {"NSE": tokens})
        
        bullish, bearish = [], []
        if quote_data['status']:
            for item in quote_data['data']['fetched']:
                # Match the fetched token back to the stock name
                stock_name = next((s["name"] for s in STOCKS_TO_TRACK if s["token"] == item['symbolToken']), "UNKNOWN")
                if item['ltp'] > item['close']: bullish.append(stock_name)
                else: bearish.append(stock_name)

        # 5. DeepSeek AI
        prompt = f"Nifty is at {current_price} (Change: {change:.2f}). Act as an expert Indian trader. Give a short 2-sentence analysis. Mention {len(bullish)} stocks are bullish and {len(bearish)} are bearish."
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        res = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json={"model": "deepseek-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500})
        ai_reply = res.json()['choices'][0]['message']['content']

        return {
            "status": "success",
            "nifty_price": current_price,
            "change": change,
            "change_percent": change_percent,
            "analysis": ai_reply,
            "bullish_list": bullish,
            "bearish_list": bearish,
            "chart_data": chart_data
        }
    except Exception as e:
        return {"error": str(e)}
