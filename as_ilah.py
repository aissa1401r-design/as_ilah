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

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
        print("Sending keyboard:", reply_markup) # اضافة للتجريب
    r = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    print("Telegram response:", r.text) # نشوفو واش قال تلغرام

def edit_buttons(chat_id, message_id): # دالة جديدة تحي الازرار
    payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
    requests.post(f"{TELEGRAM_API_URL}/editMessageReplyMarkup", json=payload)

def answer_callback(callback_id):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    supabase.table("users").insert({"chat_id": chat_id, "points": 0, "level": 1, "current_category": None}).execute()

def reset_user(chat_id):
    supabase.table("user_questions").delete().eq("chat_id", chat_id).execute()
    supabase.table("users").update({"points": 0, "level": 1}).eq("chat_id", chat_id).execute()

def get_categories(): # نجيبو الاقسام
    res = supabase.table("categories").select("*").execute()
    return res.data

def get_next_question(chat_id, category_id):
    res = supabase.table("user_questions").select("question_id").eq("chat_id", chat_id).execute()
    asked_ids = [item['question_id'] for item in res.data]

    query = supabase.table("questions").select("*").eq("category_id", category_id).order("id")
    if asked_ids:
        query = query.not_.in_("id", asked_ids)
    res = query.limit(1).execute()

    if not res.data:
        return None
    return res.data[0]

def send_question(chat_id):
    user = get_user(chat_id)
    category_id = user.get("current_category")
    if not category_id:
        send_categories(chat_id) # اذا ماخيرش قسم
        return

    question = get_next_question(chat_id, category_id)

    if not question: # كمل القسم
        user = get_user(chat_id)
        msg = f"🎉 <b>كملت قسم كامل!</b>\n\n📊 نتيجتك: {user['points']} نقطة - المستوى {user['level']}"
        keyboard = {"inline_keyboard": [[{"text": "🔄 اعادة نفس القسم", "callback_data": "confirm_reset"}],
                                        [{"text": "📚 اختار قسم جديد", "callback_data": "choose_category"}]]}
        send_message(chat_id, msg, keyboard)
        return

    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    keyboard = {"inline_keyboard": [[{"text": opt, "callback_data": f"answer_{question['id']}_{opt}"}] for opt in options]}

    msg_id = send_message(chat_id, f"❓ <b>{question['question']}</b>", keyboard)
    if msg_id:
        supabase.table("user_questions").insert({"chat_id": chat_id, "question_id": question["id"]}).execute()
        supabase.table("users").update({"last_answer": question["correct_answer"], "last_question_id": question["id"], "last_message_id": msg_id}).eq("chat_id", chat_id).execute()

def send_categories(chat_id):
    categories = get_categories()
    print("Categories from DB:", categories) # للتجريب
    
    if not categories:
        send_message(chat_id, "⚠️ مزال ما زدتش حتى قسم في الداتاباز. روح زيد في Supabase")
        return

    keyboard = {"inline_keyboard": []}
    for cat in categories:
        keyboard["inline_keyboard"].append([
            {"text": f"📖 {cat['name']}", "callback_data": f"cat_{cat['id']}"}
        ])
    
    send_message(chat_id, "📚 <b>اختار القسم اللي تحب تراجع فيه:</b>", keyboard)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        text = callback["data"]
        user = get_user(chat_id)
        answer_callback(callback["id"])

        if text.startswith("cat_"): # اختيار القسم
            cat_id = int(text.split("_")[1])
            supabase.table("users").update({"current_category": cat_id}).eq("chat_id", chat_id).execute()
            reset_user(chat_id) # نصفر قبل ما نبدا القسم الجديد
            send_message(chat_id, "✅ تم اختيار القسم. نبداو 👇")
            send_question(chat_id)
            return "ok"

        if text == "choose_category":
            send_categories(chat_id)
            return "ok"

        if text == "confirm_reset":
            reset_user(chat_id)
            send_message(chat_id, "✅ تمت اعادة القسم\nنبداو من جديد 👇")
            send_question(chat_id)
            return "ok"

        if text.startswith("answer_"):
            edit_buttons(chat_id, message_id) # نحيو الازرار من السؤال هذا

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

            send_question(chat_id)
        return "ok"

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        user = get_user(chat_id)

        if not user:
            create_user(chat_id)
            user = get_user(chat_id)
            send_message(chat_id, "مرحبا بيك في بوت الاسئلة الدينية 🌙")

        if text == "/start":
            keyboard = {"keyboard": [["سؤال جديد", "/profile", "/top"]], "resize_keyboard": True}
            send_message(chat_id, "اهلا بيك من جديد 🌙", keyboard)
            send_categories(chat_id) # نبداو باختيار القسم
            return "ok"

        elif text == "سؤال جديد":
            send_question(chat_id)

        elif text == "/profile":
            points = user['points']; level = user['level']
            remaining = (level * 60) - points
            send_message(chat_id, f"📊 <b>ملفك</b>\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining}")

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 <b>افضل 10:</b>\n" + "\n".join([f"{i}. {u['points']} نقطة" for i,u in enumerate(res.data,1)])
            send_message(chat_id, msg)

    return "ok"

@app.route("/")
def home(): return "OK", 200
