from flask import Flask, request
import os
import requests
import random
from supabase import create_client

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# قائمة اسئلة مؤقتة. من بعد نحطوها في Supabase
QUESTIONS = [
    {"q": "ما هي عاصمة الجزائر؟", "a": "الجزائر"},
    {"q": "كم عدد ايام الاسبوع؟", "a": "7"},
    {"q": "ما لون السماء؟", "a": "ازرق"},
]

def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{API_URL}/sendMessage", json=data)

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    if res.data:
        return res.data[0]
    else:
        # مستخدم جديد
        new_user = {"chat_id": chat_id, "points": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user

def update_points(chat_id, points):
    supabase.table("users").update({"points": points}).eq("chat_id", chat_id).execute()

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    print("DATA:", data)
    
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        user = get_user(chat_id)
        
        if text == "/start":
            question = random.choice(QUESTIONS)
            # نخزن الجواب الصحيح مؤقتا
            supabase.table("users").update({"last_answer": question["a"]}).eq("chat_id", chat_id).execute()
            
            keyboard = {
                "keyboard": [["سؤال جديد"]],
                "resize_keyboard": True
            }
            send_message(chat_id, f"مرحبا! ✅\nنقاطك: {user['points']}\n\nالسؤال: {question['q']}", keyboard)
        
        elif text == "سؤال جديد":
            question = random.choice(QUESTIONS)
            supabase.table("users").update({"last_answer": question["a"]}).eq("chat_id", chat_id).execute()
            send_message(chat_id, f"السؤال: {question['q']}")
        
        else: # هذا جواب المستخدم
            correct_answer = user.get("last_answer", "")
            if text.strip() == correct_answer:
                new_points = user["points"] + 10
                update_points(chat_id, new_points)
                send_message(chat_id, f"صحيح! +10 نقاط 🎉\nنقاطك: {new_points}")
            else:
                send_message(chat_id, f"غلط 😅\nالجواب الصحيح: {correct_answer}\nنقاطك: {user['points']}")

    return "ok", 200 

@app.route("/")
def home():
    return "OK", 200
