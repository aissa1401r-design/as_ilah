import os
import random
import requests
from flask import Flask, request
from supabase import create_client, Client

app = Flask(__name__)

# 1. حط التوكن والرابط تاعك
BOT_TOKEN = "حط_التوكن_تاعك_هنا"
SUPABASE_URL = "حط_الرابط_تاعك_هنا"
SUPABASE_KEY = "حط_key_تاعك_هنا"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. الدالة الجديدة باش نجيبو سؤال من قاعدة البيانات
def get_random_question():
    res = supabase.table("questions").select("*").execute()
    if res.data:
        return random.choice(res.data)
    return None

# 3. الدالة الجديدة باش نبعثو السؤال بالازرار
def send_question(chat_id, question):
    if not question: return

    # نجمعو ال4 اختيارات ونخلطوهم
    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    random.shuffle(options)

    keyboard = {
        "keyboard": [[opt] for opt in options] + [["سؤال جديد", "/profile", "/top"]],
        "resize_keyboard": True
    }

    # نخزنو الجواب الصحيح
    supabase.table("users").update({"last_answer": question["correct_answer"]}).eq("chat_id", chat_id).execute()

    send_message(chat_id, f"❓ السؤال: {question['question']}", keyboard)

def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    new_user = {"chat_id": chat_id, "points": 0, "level": 1}
    supabase.table("users").insert(new_user).execute()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        user = get_user(chat_id)
        if not user:
            create_user(chat_id)
            user = get_user(chat_id)
            question = get_random_question()
            send_question(chat_id, question)
            return "ok"

        if text == "/start":
            question = get_random_question()
            send_question(chat_id, question)

        elif text == "سؤال جديد":
            question = get_random_question()
            send_question(chat_id, question)

        elif text == "/profile":
            points = user['points']
            level = user['level']
            next_level_points = level * 60
            remaining = next_level_points - points
            msg = f"📊 ملفك الشخصي\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining} نقطة للمستوى {level+1}"
            send_message(chat_id, msg)

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 افضل 10 لاعبين:\n"
            for i, u in enumerate(res.data, 1):
                msg += f"{i}. نقاط: {u['points']} - مستوى: {u['level']}\n"
            send_message(chat_id, msg)

        else: # هنا يشيك الاجابة
            correct_answer = user['last_answer']
            if text == correct_answer:
                new_points = user['points'] + 10
                new_level = user['level']
                if new_points >= new_level * 60:
                    new_level += 1
                    send_message(chat_id, f"🎉 مبروك! طلعت للمستوى {new_level}")

                supabase.table("users").update({"points": new_points, "level": new_level}).eq("chat_id", chat_id).execute()
                send_message(chat_id, f"✅ صحيح! +10 نقاط\nالمجموع: {new_points}")

                question = get_random_question() # سؤال جديد اوتوماتيك
                send_question(chat_id, question)
            else:
                send_message(chat_id, f"❌ خطأ! الجواب الصحيح هو: {correct_answer}")
                question = get_random_question()
                send_question(chat_id, question)

    return "ok"

@app.route("/")
def home():
    return "OK", 200

if name == "__main__":
    app.run(host="0.0.0.0", port=5000)
