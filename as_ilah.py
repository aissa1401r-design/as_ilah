from flask import Flask, request
import os
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})
    except:
        pass

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    print("DATA:", data) # باش نشوفو في Logs
    
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if text == "/start":
            send_message(chat_id, "مرحبا! البوت خدام الآن ✅\nنقاطك: 0")
        else:
            send_message(chat_id, f"وصلتني: {text}")
    
    # هذا اهم سطر - لازم ديما يرجع ok
    return "ok", 200 

@app.route("/")
def home():
    return "OK", 200
