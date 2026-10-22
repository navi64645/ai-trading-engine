from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from SmartApi import SmartConnect
import requests
import os
import time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- MEMORY TO SAVE MONEY ---
last_ai_signal = None
last_nifty_price = 0
last_update_time = 0

INDICES_AND_COMMODITIES = [
    {"name": "NIFTY 50", "token": "26000", "exchange": "NSE"},
    {"name": "BANK NIFTY", "token": "26009", "exchange": "NSE"},
    {"name": "CRUDE OIL", "token": "1140026", "exchange": "MCX"},
    {"name": "GOLD", "token": "1140027", "exchange": "MCX"},
    {"name": "SILVER", "token": "1140028", "exchange": "MCX"}
]

STOCKS_TO_TRACK = [
    {"name": "RELIANCE", "token": "2885"}, {"name": "HDFCBANK", "token": "1333"},
    {"name": "ICICIBANK", "token": "4963"}, {"name": "TCS", "token": "11536"},
    {"name": "INFY", "token": "1594"}, {"name": "SBIN", "token": "3045"},
    {"name": "ITC", "token": "1660"}, {"name": "BHARTIARTL", "token": "10604"},
    {"name": "HINDUNILVR", "token": "1394"}, {"name": "LT", "token": "11483"},
    {"name": "KOTAKBANK", "token": "1922"}, {"name": "AXISBANK", "token": "5900"},
    {"name": "TATAMOTORS", "token": "3456"}, {"name": "TATASTEEL", "token": "3499"},
    {"name": "M&M", "token": "2031"}, {"name": "BAJFINANCE", "token": "317"},
    {"name": "ASIANPAINT", "token": "236"}, {"name": "MARUTI", "token": "10999"},
    {"name": "HCLTECH", "token": "7229"}, {"name": "SUNPHARMA", "token": "3351"},
    {"name": "TITAN", "token": "3506"}, {"name": "ULTRACEMCO", "token": "11532"},
    {"name": "WIPRO", "token": "3787"}, {"name": "ADANIENT", "token": "25"},
    {"name": "ADANIPORTS", "token": "15083"}, {"name": "POWERGRID", "token": "14977"},
    {"name": "NTPC", "token": "11630"}, {"name": "TECHM", "token": "13538"},
    {"name": "HINDALCO", "token": "1363"}, {"name": "INDUSINDBK", "token": "5258"},
    {"name": "NESTLEIND", "token": "17963"}, {"name": "JSWSTEEL", "token": "11723"},
    {"name": "GRASIM", "token": "1232"}, {"name": "CIPLA", "token": "694"},
    {"name": "DRREDDY", "token": "881"}, {"name": "EICHERMOT", "token": "910"},
    {"name": "HEROMOTOCO", "token": "1348"}, {"name": "DIVISLAB", "token": "10940"},
    {"name": "BPCL", "token": "526"}, {"name": "BRITANNIA", "token": "547"},
    {"name": "COALINDIA", "token": "20374"}, {"name": "APOLLOHOSP", "token": "157"},
    {"name": "TATACONSUM", "token": "3432"}, {"name": "SBILIFE", "token": "21808"},
    {"name": "HDFCLIFE", "token": "467"}, {"name": "BAJAJ-AUTO", "token": "16669"},
    {"name": "SHRIRAMFIN", "token": "17048"}, {"name": "ONGC", "token": "2475"},
    {"name": "UPL", "token": "11287"}, {"name": "TATAPOWER", "token": "3426"},
    {"name": "DLF", "token": "14732"}, {"name": "PIDILITIND", "token": "2664"},
    {"name": "GODREJCP", "token": "10099"}, {"name": "DABUR", "token": "772"},
    {"name": "HAVELLS", "token": "9819"}, {"name": "SIEMENS", "token": "3150"},
    {"name": "ABFRL", "token": "30125"}, {"name": "ZOMATO", "token": "5097"},
    {"name": "PAYTM", "token": "6705"}, {"name": "NYKAA", "token": "6545"},
    {"name": "IRCTC", "token": "13611"}, {"name": "PNB", "token": "10666"},
    {"name": "BANKBARODA", "token": "4668"}, {"name": "CANBK", "token": "10794"},
    {"name": "IDFCFIRSTB", "token": "11184"}, {"name": "FEDERALBNK", "token": "1023"},
    {"name": "RBLBANK", "token": "4708"}, {"name": "AUBANK", "token": "21238"},
    {"name": "BANDHANBNK", "token": "2263"}, {"name": "YESBANK", "token": "11915"},
    {"name": "IDEA", "token": "14366"}, {"name": "GMRINFRA", "token": "13528"},
    {"name": "BEL", "token": "383"}, {"name": "HAL", "token": "2303"},
    {"name": "BHEL", "token": "438"}, {"name": "SAIL", "token": "2963"},
    {"name": "NMDC", "token": "15332"}, {"name": "VEDL", "token": "3063"},
    {"name": "JINDALSTEL", "token": "11654"}, {"name": "LUPIN", "token": "10440"},
    {"name": "AUROPHARMA", "token": "275"}, {"name": "ALKEM", "token": "11703"},
    {"name": "TORNTPHARM", "token": "3518"}, {"name": "ZYDUSLIFE", "token": "12806"},
    {"name": "GLENMARK", "token": "7406"}, {"name": "BIOCON", "token": "11373"},
    {"name": "LTI", "token": "17818"}, {"name": "MPHASIS", "token": "4503"},
    {"name": "PERSISTENT", "token": "18365"}, {"name": "COFORGE", "token": "10738"},
    {"name": "LTTS", "token": "18564"}, {"name": "OFSS", "token": "10738"},
    {"name": "TATACHEM", "token": "3405"}, {"name": "SRF", "token": "3277"},
    {"name": "PIIND", "token": "24184"}, {"name": "UPL", "token": "11287"},
    {"name": "BAYERCROP", "token": "11682"}, {"name": "COROMANDEL", "token": "15141"},
    {"name": "CHAMBLFERT", "token": "11855"}, {"name": "GNFC", "token": "10032"},
    {"name": "RCF", "token": "11369"}, {"name": "DEEPAKNTR", "token": "11661"},
    {"name": "ATUL", "token": "8858"}, {"name": "NAVINFLUOR", "token": "10940"},
    {"name": "FLUOROCHEM", "token": "29678"}, {"name": "AARTIIND", "token": "14418"},
    {"name": "TATACOMM", "token": "3721"}, {"name": "IDEA", "token": "14366"}
]

@app.get("/")
def read_root(): return {"status": "API is running!"}

@app.get("/api/analyze")
def get_analysis():
    global last_ai_signal, last_nifty_price, last_update_time
    
    try:
        API_KEY, CLIENT_CODE = os.environ.get("API_KEY"), os.environ.get("CLIENT_CODE")
        MPIN, TOTP_SECRET = os.environ.get("MPIN"), os.environ.get("TOTP_SECRET")
        DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

        totp = pyotp.TOTP(TOTP_SECRET)
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, totp.now())
        
        # 1. Get Indices & Commodities
        indices_data = []
        for item in INDICES_AND_COMMODITIES:
            quote = smartApi.ltpData(item["exchange"], item["name"], item["token"])
            if quote['status']:
                indices_data.append({"name": item["name"], "price": quote['data']['ltp']})

        # 2. Get Stocks Breadth
        tokens = [s["token"] for s in STOCKS_TO_TRACK]
        quote_data = smartApi.getMarketData("FULL", {"NSE": tokens})
        
        bullish, bearish = [], []
        if quote_data['status']:
            for item in quote_data['data']['fetched']:
                name = next((s["name"] for s in STOCKS_TO_TRACK if s["token"] == item['symbolToken']), "UNKNOWN")
                if item['ltp'] > item['close']: bullish.append(name)
                else: bearish.append(name)

        total = len(bullish) + len(bearish)
        bull_pct = round((len(bullish) / total) * 100, 1) if total > 0 else 0
        bear_pct = round((len(bearish) / total) * 100, 1) if total > 0 else 0
        
        nifty_price = next((i["price"] for i in indices_data if i["name"] == "NIFTY 50"), 0)
        current_time = time.time()

        # 3. SMART DEEPSEEK LOGIC (SAVES MONEY)
        # Only call AI if price changed by > 5 points, OR if 5 minutes passed
        if last_ai_signal is None or abs(nifty_price - last_nifty_price) > 5 or (current_time - last_update_time > 300):
            
            prompt = f"""
            Nifty is at {nifty_price}. Bullish stocks: {bull_pct}%, Bearish stocks: {bear_pct}%.
            Act as an aggressive intraday trader. 
            Give a direct verdict: Should I buy a CALL or a PUT right now? 
            Provide the exact Target and Stop Loss in 2 sentences. Do not give a neutral answer.
            """
            
            headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
            res = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json={"model": "deepseek-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150})
            
            # Save the new signal
            last_ai_signal = res.json()['choices'][0]['message']['content']
            last_nifty_price = nifty_price
            last_update_time = current_time
        else:
            # Price didn't move enough. Return the OLD signal. (Costs 0 tokens!)
            pass

        return {
            "status": "success",
            "indices": indices_data,
            "bullish_pct": bull_pct,
            "bearish_pct": bear_pct,
            "bullish_list": bullish,
            "bearish_list": bearish,
            "ai_signal": last_ai_signal
        }

    except Exception as e:
        return {"error": str(e)}
