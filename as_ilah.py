from flask import Flask, request
import os
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    print("DATA:", data) # باش نشوفو في Logs
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        
        if text == "/start":
            send_message(chat_id, "مرحبا! البوت خدام ✅")
            
    return "ok", 200

@app.route("/")
def home():
    return "OK"
