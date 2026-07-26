import os
import requests
from flask import Flask, request

SHOP_NAME = os.environ.get("SHOP_NAME", "متجري")
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

def send_message(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        if text == "/start":
            send_message(chat_id, f"مرحبا بك في {SHOP_NAME}\nأي شيء تريدينه اليوم")
    return "ok", 200

@app.get("/")
def home():
    return "OK", 200

@app.get("/setwebhook")
def set_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if render_url and not render_url.startswith("https://"):
        render_url = "https://" + render_url
    url = f"{API_URL}/setWebhook?url={render_url}/{TOKEN}"
    r = requests.get(url)
    return r.text, 200
