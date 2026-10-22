from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from SmartApi import SmartConnect
import requests
import os
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, totp.now())
        if not data['status']: return {"error": "Angel One Login Failed"}

        # 2. Get Nifty Full Quote (for real price change)
        quote = smartApi.getMarketData({"mode": "FULL", "exchangeTokens": {"NSE": ["26000"]}})
        live_data = quote['data']['fetched'][0]
        current_price = live_data['ltp']
        prev_close = live_data['close']
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        # 3. Get Historical Chart Data (Past 1 Day, 5-minute candles)
        # Angel One needs time in ISO format
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
        
        historicParam = {
            "exchange": "NSE",
            "symboltoken": "26000",
            "interval": "FIVE_MINUTE",
            "fromdate": from_date,
            "todate": to_date
        }
        hist_data = smartApi.getCandleData(historicParam)
        
        chart_data = []
        if hist_data['status']:
            for candle in hist_data['data']:
                # Format: [Timestamp, Open, High, Low, Close, Volume]
                chart_data.append({
                    "time": candle[0], # This comes as an array [YYYY, M, D, H, M]
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4])
                })

        # 4. Get Live Stock Data
        bullish_stocks, bearish_stocks = [], []
        for stock in STOCKS_TO_TRACK:
            q = smartApi.getMarketData({"mode": "FULL", "exchangeTokens": {stock["exchange"]: [stock["token"]]}})
            if q['status']:
                d = q['data']['fetched'][0]
                if d['ltp'] > d['close']: bullish_stocks.append(stock["name"])
                else: bearish_stocks.append(stock["name"])

        # 5. Ask DeepSeek
        prompt = f"Nifty 50 is at {current_price} with a change of {change:.2f}. Act as an expert Indian trader. Give a short 2-sentence analysis. Mention {len(bullish_stocks)} stocks are bullish and {len(bearish_stocks)} are bearish."
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500}
        res = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        ai_reply = res.json()['choices'][0]['message']['content']

        # 6. Send EVERYTHING to Frontend
        return {
            "status": "success",
            "nifty_price": current_price,
            "change": change,
            "change_percent": change_percent,
            "analysis": ai_reply,
            "bullish_list": bullish_stocks,
            "bearish_list": bearish_stocks,
            "chart_data": chart_data  # <--- REAL CANDLESTICK DATA
        }

    except Exception as e:
        return {"error": str(e)}
