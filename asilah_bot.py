import os
import requests
from flask import Flask, request

SHOPE_NAME=os.environ.get("SHOPE_NAME")
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, f"مرحبا بك في متجرك: {SHOPE_NAME} \n أي شيئ تريدينه اليوم")

    return "ok"

@app.get("/")
def home():
    return "OK"

@app.get("/setwebhook")
def set_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    url = f"{API_URL}/setWebhook?url={render_url}/{TOKEN}"
    r = requests.get(url)
    return r.text
