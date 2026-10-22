from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from SmartApi import SmartConnect
import requests
import os
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Nifty 50 constituents (name + token)
NIFTY_50_STOCKS = [
    {"name": "RELIANCE", "token": "2885"}, {"name": "HDFCBANK", "token": "1333"},
    {"name": "ICICIBANK", "token": "4963"}, {"name": "TCS", "token": "11536"},
    {"name": "INFY", "token": "1594"}, {"name": "SBIN", "token": "3045"},
    {"name": "ITC", "token": "1660"}, {"name": "BHARTIARTL", "token": "10604"},
    {"name": "HINDUNILVR", "token": "1394"}, {"name": "LT", "token": "11483"},
    {"name": "KOTAKBANK", "token": "1922"}, {"name": "AXISBANK", "token": "5900"},
    {"name": "BAJFINANCE", "token": "317"}, {"name": "ASIANPAINT", "token": "236"},
    {"name": "MARUTI", "token": "10999"}, {"name": "HCLTECH", "token": "7229"},
    {"name": "SUNPHARMA", "token": "3351"}, {"name": "TITAN", "token": "3506"},
    {"name": "ULTRACEMCO", "token": "11532"}, {"name": "WIPRO", "token": "3787"},
    {"name": "ADANIENT", "token": "25"}, {"name": "ADANIPORTS", "token": "15083"},
    {"name": "POWERGRID", "token": "14977"}, {"name": "NTPC", "token": "11630"},
    {"name": "TATAMOTORS", "token": "3456"}, {"name": "TATASTEEL", "token": "3499"},
    {"name": "M&M", "token": "2031"}, {"name": "BAJAJFINSV", "token": "16675"},
    {"name": "TECHM", "token": "13538"}, {"name": "HINDALCO", "token": "1363"},
    {"name": "INDUSINDBK", "token": "5258"}, {"name": "NESTLEIND", "token": "17963"},
    {"name": "JSWSTEEL", "token": "11723"}, {"name": "GRASIM", "token": "1232"},
    {"name": "CIPLA", "token": "694"}, {"name": "DRREDDY", "token": "881"},
    {"name": "EICHERMOT", "token": "910"}, {"name": "HEROMOTOCO", "token": "1348"},
    {"name": "DIVISLAB", "token": "10940"}, {"name": "BPCL", "token": "526"},
    {"name": "BRITANNIA", "token": "547"}, {"name": "COALINDIA", "token": "20374"},
    {"name": "APOLLOHOSP", "token": "157"}, {"name": "TATACONSUM", "token": "3432"},
    {"name": "SBILIFE", "token": "21808"}, {"name": "HDFCLIFE", "token": "467"},
    {"name": "BAJAJ-AUTO", "token": "16669"}, {"name": "SHRIRAMFIN", "token": "17048"},
    {"name": "ONGC", "token": "2475"}, {"name": "UPL", "token": "11287"}
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
        if not data['status']: return {"error": "Angel One Login Failed"}

        # 2. Nifty live price
        nifty_quote = smartApi.ltpData("NSE", "NIFTY", "26000")
        current_price = nifty_quote['data']['ltp']
        nifty_full = smartApi.getMarketData("FULL", {"NSE": ["26000"]})
        prev_close = nifty_full['data']['fetched'][0]['close']
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        # 3. Chart data
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
        hist_data = smartApi.getCandleData({
            "exchange": "NSE", "symboltoken": "26000", "interval": "FIVE_MINUTE",
            "fromdate": from_date, "todate": to_date
        })
        chart_data = [{"time": c[0], "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in hist_data['data']] if hist_data['status'] else []

        # 4. Batch query Nifty 50 stocks for breadth (API supports up to 50 symbols)
        all_tokens = [s["token"] for s in NIFTY_50_STOCKS]
        # Split into groups of 50 (Nifty 50 fits in one group)
        batch = all_tokens[:50]
        quote_data = smartApi.getMarketData("FULL", {"NSE": batch})
        
        bullish, bearish = [], []
        stock_details = []
        
        if quote_data['status']:
            for item in quote_data['data']['fetched']:
                stock_name = next((s["name"] for s in NIFTY_50_STOCKS if s["token"] == item['symbolToken']), "UNKNOWN")
                is_bullish = item['ltp'] > item['close']
                if is_bullish:
                    bullish.append(stock_name)
                else:
                    bearish.append(stock_name)
                stock_details.append({
                    "name": stock_name,
                    "price": item['ltp'],
                    "change": round(item['ltp'] - item['close'], 2),
                    "change_pct": round((item['ltp'] - item['close']) / item['close'] * 100, 2),
                    "bullish": is_bullish
                })

        total = len(bullish) + len(bearish)
        bull_pct = round(len(bullish) / total * 100, 1) if total > 0 else 0
        bear_pct = round(len(bearish) / total * 100, 1) if total > 0 else 0

        # 5. DeepSeek AI
        prompt = f"Nifty is at {current_price} (Change: {change:.2f}). Act as an expert Indian trader. Give a short 2-sentence analysis. {len(bullish)} out of {total} stocks are bullish ({bull_pct}%) and {len(bearish)} are bearish ({bear_pct}%)."
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
            "bullish_pct": bull_pct,
            "bearish_pct": bear_pct,
            "stock_details": stock_details,
            "chart_data": chart_data
        }
    except Exception as e:
        return {"error": str(e)}
