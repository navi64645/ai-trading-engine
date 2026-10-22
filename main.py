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

        totp = pyotp.TOTP(TOTP_SECRET)
        current_otp = totp.now()
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_CODE, MPIN, current_otp)
        
        if not data['status']:
            return {"error": "Angel One Login Failed", "details": data['message']}

        params = {"exchange": "NSE", "tradingsymbol": "NIFTY", "symboltoken": "26000"}
        ltp_data = smartApi.ltpData(params["exchange"], params["tradingsymbol"], params["symboltoken"])
        
        if not ltp_data['status']:
            return {"error": "Could not fetch NIFTY data"}
            
        nifty_price = ltp_data['data']['ltp']

        prompt = f"The Nifty 50 current price is {nifty_price}. Act as an expert Indian stock market trader. Give me a very short 2-sentence analysis of the market direction right now."
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }
        
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        ai_reply = response.json()['choices'][0]['message']['content']

        return {
            "status": "success",
            "price": nifty_price,
            "analysis": ai_reply
        }

    except Exception as e:
        return {"error": str(e)}