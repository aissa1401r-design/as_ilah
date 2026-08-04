import os
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
    r = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    return r.status_code == 200

def answer_callback(callback_id):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    supabase.table("users").insert({"chat_id": chat_id, "points": 0, "level": 1}).execute()

def reset_user(chat_id):
    supabase.table("user_questions").delete().eq("chat_id", chat_id).execute()
    supabase.table("users").update({"points": 0, "level": 1}).eq("chat_id", chat_id).execute()

def get_next_question(chat_id):
    res = supabase.table("user_questions").select("question_id").eq("chat_id", chat_id).execute()
    asked_ids = [item['question_id'] for item in res.data]

    query = supabase.table("questions").select("*").order("id")
    if asked_ids:
        query = query.not_.in_("id", asked_ids)
    res = query.limit(1).execute()

    if not res.data: # كمل كل الاسئلة
        return None
    return res.data[0]

def send_question(chat_id):
    question = get_next_question(chat_id)

    # 1. اذا كمل كل الاسئلة
    if not question:
        user = get_user(chat_id)
        points = user['points']; level = user['level']
        remaining_to_next = (level * 60) - points

        msg = f"🎉 <b>مبروك كملت كل الاسئلة!</b>\n\n"
        msg += f"📊 <b>نتيجتك النهائية</b>\n"
        msg += f"المستوى: {level}\n"
        msg += f"النقاط: {points}\n"
        msg += f"باقيلك {remaining_to_next} للمستوى الجاي\n\n"
        msg += f"تحب تعاود الاختبار من جديد؟"

        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 اعادة الاختبار", "callback_data": "confirm_reset"}]
            ]
        }
        send_message(chat_id, msg, keyboard)
        return

    # 2. اذا مزال كاين اسئلة
    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    keyboard = {"inline_keyboard": [[{"text": opt, "callback_data": f"answer_{question['id']}_{opt}"}] for opt in options]}

    sent = send_message(chat_id, f"❓ <b>{question['question']}</b>", keyboard)

    if sent:
        supabase.table("user_questions").insert({"chat_id": chat_id, "question_id": question["id"]}).execute()
        supabase.table("users").update({"last_answer": question["correct_answer"], "last_question_id": question["id"]}).eq("chat_id", chat_id).execute()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        text = callback["data"]
        user = get_user(chat_id)
        answer_callback(callback["id"])

        if text == "confirm_reset": # زر اعادة الاختبار
            reset_user(chat_id)
            send_message(chat_id, "✅ تم تصفير النقاط والاسئلة\nنبداو دورة جديدة 👇")
            send_question(chat_id)
            return "ok"

        if text.startswith("answer_"):
            parts = text.split("_", 2)
            user_answer = parts[2]
            correct = user.get('last_answer', "")

            if user_answer == correct:
                new_points = user['points'] + 10; new_level = user['level']
                msg = f"✅ صحيح! +10 نقاط\nالمجموع: {new_points}"
                if new_points >= new_level * 60:
                    new_level += 1
                    msg = f"🎉 مبروك! طلعت للمستوى {new_level}\n" + msg
                supabase.table("users").update({"points": new_points, "level": new_level}).eq("chat_id", chat_id).execute()
                send_message(chat_id, msg)
            else:
                send_message(chat_id, f"❌ خطأ! الصحيح هو: <b>{correct}</b>")

            send_question(chat_id) # السؤال الجاي
        return "ok"

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
            keyboard = {"keyboard": [["سؤال جديد", "/profile", "/top"]], "resize_keyboard": True} # نحينا /reset
            send_message(chat_id, "اهلا بيك من جديد 🌙", keyboard)
            send_question(chat_id)
            return "ok"

        elif text == "سؤال جديد":
            send_question(chat_id)

        elif text == "/profile":
            points = user['points']; level = user['level']
            remaining = (level * 60) - points
            send_message(chat_id, f"📊 <b>ملفك الحالي</b>\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining}")

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 <b>افضل 10:</b>\n" + "\n".join([f"{i}. {u['points']} نقطة" for i,u in enumerate(res.data,1)])
            send_message(chat_id, msg)

    return "ok"

@app.route("/")
def home(): return "OK", 200
