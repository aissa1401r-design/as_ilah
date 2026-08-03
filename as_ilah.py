import os
import random
import requests
import json
from flask import Flask, request
from supabase import create_client, Client

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    supabase.table("users").insert({"chat_id": chat_id, "points": 0, "level": 1}).execute()

def get_random_question(chat_id):
    # 1. نجيبو id الاسئلة اللي جازو على المستخدم
    res = supabase.table("user_questions").select("question_id").eq("chat_id", chat_id).execute()
    asked_ids = [item['question_id'] for item in res.data]

    # 2. نجيبو سؤال جديد
    query = supabase.table("questions").select("*")
    if asked_ids:
        query = query.not_.in_("id", asked_ids)
    res = query.execute()

    # 3. اذا كملو الاسئلة نعاودو من الصفر
    if not res.data:
        send_message(chat_id, "🔄 كملت كل الاسئلة! نبداو دورة جديدة")
        supabase.table("user_questions").delete().eq("chat_id", chat_id).execute()
        res = supabase.table("questions").select("*").execute()

    new_q = random.choice(res.data)

    # 4. نسجلو بلي السؤال هذا "جاز"
    supabase.table("user_questions").insert({"chat_id": chat_id, "question_id": new_q["id"]}).execute()
    return new_q

def send_question(chat_id, question):
    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    random.shuffle(options)
    keyboard = {"keyboard": [[opt] for opt in options] + [["سؤال جديد", "/profile", "/top"]], "resize_keyboard": True}
    supabase.table("users").update({"last_answer": question["correct_answer"]}).eq("chat_id", chat_id).execute()
    send_message(chat_id, f"❓ {question['question']}", keyboard)

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
            send_message(chat_id, "مرحبا بيك في بوت الاسئلة الدينية 🌙")
            q = get_random_question(chat_id)
            if q: send_question(chat_id, q)
            return "ok"

        if text == "/start":
            send_message(chat_id, "اهلا بيك من جديد 🌙")
            q = get_random_question(chat_id)
            if q: send_question(chat_id, q)
            return "ok"

        elif text == "سؤال جديد":
            q = get_random_question(chat_id)
            if q: send_question(chat_id, q)

        elif text == "/profile":
            points = user['points']; level = user['level']
            remaining = (level * 60) - points
            send_message(chat_id, f"📊 ملفك\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining}")

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 افضل 10:\n" + "\n".join([f"{i}. {u['points']} نقطة" for i,u in enumerate(res.data,1)])
            send_message(chat_id, msg)

        else: # الاجابة
            correct = user.get('last_answer', "")
            if text == correct:
                new_points = user['points'] + 10; new_level = user['level']
                if new_points >= new_level * 60: new_level += 1; send_message(chat_id, f"🎉 مستوى {new_level}")
                supabase.table("users").update({"points": new_points, "level": new_level}).eq("chat_id", chat_id).execute()
                send_message(chat_id, f"✅ صحيح! +10\nالمجموع: {new_points}")
            else:
                send_message(chat_id, f"❌ خطأ! الصح: {correct}")

            q = get_random_question(chat_id)
            if q: send_question(chat_id, q)

    return "ok"

@app.route("/")
def home(): return "OK", 200
