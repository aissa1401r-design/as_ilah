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
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def edit_message(chat_id, message_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(f"{TELEGRAM_API_URL}/editMessageText", json=payload)

def answer_callback(callback_id):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    supabase.table("users").insert({"chat_id": chat_id, "points": 0, "level": 1}).execute()

def get_random_question(chat_id):
    res = supabase.table("user_questions").select("question_id").eq("chat_id", chat_id).execute()
    asked_ids = [item['question_id'] for item in res.data]

    query = supabase.table("questions").select("*")
    if asked_ids:
        query = query.not_.in_("id", asked_ids)
    res = query.execute()

    if not res.data: # اذا كمل
        supabase.table("user_questions").delete().eq("chat_id", chat_id).execute()
        res = supabase.table("questions").select("*").execute()
        if not res.data: return None

    new_q = random.choice(res.data)
    supabase.table("user_questions").insert({"chat_id": chat_id, "question_id": new_q["id"]}).execute()
    return new_q

def send_question(chat_id):
    question = get_random_question(chat_id)
    if not question:
        send_message(chat_id, "🔄 ما كاين حتى سؤال في قاعدة البيانات")
        return

    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    random.shuffle(options)

    # ازرار inline مربوطة بالاجابة
    keyboard = {
    "inline_keyboard": [
        [
            {"text": options[0], "callback_data": f"answer_{options[0]}"},
            {"text": options[1], "callback_data": f"answer_{options[1]}"}
        ],
        [
            {"text": options[2], "callback_data": f"answer_{options[2]}"},
            {"text": options[3], "callback_data": f"answer_{options[3]}"}
        ]
    ]
}


    # نحفظو الاجابة الصحيحة في جدول users
    supabase.table("users").update({"last_answer": question["correct_answer"], "last_question_id": question["id"]}).eq("chat_id", chat_id).execute()
    send_message(chat_id, f"❓ <b>{question['question']}</b>", keyboard)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    # 1. اذا ضغط على زر
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        text = callback["data"]
        user = get_user(chat_id)
        answer_callback(callback["id"])

        if text.startswith("answer_"):
            user_answer = text.replace("answer_", "")
            correct = user.get('last_answer', "")

            if user_answer == correct:
                new_points = user['points'] + 10; new_level = user['level']
                if new_points >= new_level * 60:
                    new_level += 1
                    edit_message(chat_id, message_id, f"🎉 مبروك! طلعت للمستوى {new_level}")
                supabase.table("users").update({"points": new_points, "level": new_level}).eq("chat_id", chat_id).execute()
                edit_message(chat_id, message_id, f"✅ صحيح! +10 نقاط\nالمجموع: {new_points}")
            else:
                edit_message(chat_id, message_id, f"❌ خطأ! الصحيح هو: <b>{correct}</b>")

            send_question(chat_id) # نبعثو السؤال الجاي ديركت
        return "ok"
    # 2. اذا بعث رسالة
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        user = get_user(chat_id)

        if not user:
            create_user(chat_id)
            user = get_user(chat_id)
            send_message(chat_id, "مرحبا بيك في بوت الاسئلة الدينية 🌙")
            send_question(chat_id)
            return "ok"

        if text == "/start":
            keyboard = {"keyboard": [["سؤال جديد", "/profile", "/top"]], "resize_keyboard": True}
            send_message(chat_id, "اهلا بيك من جديد 🌙", keyboard)
            send_question(chat_id)
            return "ok"

        elif text == "سؤال جديد":
            send_question(chat_id)

        elif text == "/profile":
            points = user['points']; level = user['level']
            remaining = (level * 60) - points
            send_message(chat_id, f"📊 <b>ملفك</b>\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining} للمستوى الجاي")

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 <b>افضل 10:</b>\n" + "\n".join([f"{i}. {u['points']} نقطة" for i,u in enumerate(res.data,1)])
            send_message(chat_id, msg)

    return "ok"

@app.route("/")
def home(): return "OK", 200
