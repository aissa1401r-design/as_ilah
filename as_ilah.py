import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
SHOP_NAME = "بوت الأسئلة الدينية"

# 1. دالة الارسال مطورة
def send_message(chat_id, text, keyboard=None):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    
    try:
        r = requests.post(url, json=payload, timeout=5)
        print("Telegram response:", r.status_code, r.text)
    except Exception as e:
        print("Error:", e)

# 2. الازرار الرئيسية
main_keyboard = {
    "keyboard": [
        ["📖 ابدأ الاختبار"],
        ["🏆 النتيجة"], 
        ["❓ مساعدة"]
    ],
    "resize_keyboard": True,  # تصغر الازرار
    "one_time_keyboard": False # تبقى دايما
}

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}
    print("Data:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            msg = f"مرحبا بك في {SHOP_NAME}\nاختار من القائمة تحت 👇"
            send_message(chat_id, msg, main_keyboard)

        elif text == "📖 ابدأ الاختبار":
            send_message(chat_id, "بسم الله نبداو\nالسؤال الاول: كم عدد أركان الاسلام؟", main_keyboard)
        
        elif text == "🏆 النتيجة":
            send_message(chat_id, "مازال ما جاوبت على حتى سؤال 😅", main_keyboard)

        elif text == "❓ مساعدة":
            send_message(chat_id, "هذا بوت أسئلة دينية\nاضغط ابدأ الاختبار و جاوب على الأسئلة", main_keyboard)
        
        else:
            send_message(chat_id, "اختار من الازرار تحت 👇", main_keyboard)

    return "ok", 200

@app.get("/")
def health_check():
    return "Bot is running", 200
