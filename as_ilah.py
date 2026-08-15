import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(_name_) # 1. صلحتها هنا

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    r = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    data = r.json()
    if data.get("ok"):
        return data["result"]["message_id"]
    return None

def edit_buttons(chat_id, message_id):
    payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
    requests.post(f"{TELEMAIL_API_URL}/editMessageReplyMarkup", json=payload)

def answer_callback(callback_id):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def create_user(chat_id):
    supabase.table("users").insert({"chat_id": chat_id, "points": 0, "level": 1, "current_category": None}).execute()

def reset_user(chat_id):
    supabase.table("user_questions").delete().eq("chat_id", chat_id).execute()
    supabase.table("users").update({"points": 0, "level": 1, "current_category": None}).eq("chat_id", chat_id).execute()

def get_categories():
    res = supabase.table("categories").select("*").execute()
    return res.data

def get_question_by_id(q_id):
    res = supabase.table("questions").select("*").eq("id", q_id).single().execute()
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
        send_categories(chat_id)
        return

    question = get_next_question(chat_id, category_id)

    if not question:
        user = get_user(chat_id)
        msg = f"🎉 <b>كملت قسم كامل!</b>\n\n📊 نتيجتك: {user['points']} نقطة - المستوى {user['level']}"
        keyboard = {"inline_keyboard": [[{"text": "🔄 اعادة نفس القسم", "callback_data": "confirm_reset"}],
                                        [{"text": "📚 اختار قسم جديد", "callback_data": "choose_category"}]]}
        send_message(chat_id, msg, keyboard)
        return

    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    keyboard = {"inline_keyboard": [[{"text": opt, "callback_data": f"answer_{question['id']}_{opt}"}] for opt in options]}

    send_message(chat_id, f"❓ <b>{question['question']}</b>", keyboard)
    supabase.table("user_questions").insert({"chat_id": chat_id, "question_id": question["id"]}).execute()

def send_categories(chat_id):
    categories = get_categories()
    if not categories:
        send_message(chat_id, "⚠️ مزال ما زدتش حتى قسم في الداتاباز. روح زيد في Supabase")
        return

    keyboard = {"inline_keyboard": []}
    for cat in categories:
        keyboard["inline_keyboard"].append([{"text": f"📖 {cat['name']}", "callback_data": f"cat_{cat['id']}"}])

    send_message(chat_id, "📚 <b>اختار القسم اللي تحب تراجع فيه:</b>", keyboard)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    print("Update received:", update) # باش تشوف في Logs
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        user = get_user(chat_id)

        if not user:
            create_user(chat_id)
            send_message(chat_id, "مرحبا بيك! 👋")

        if text == "/start":
            send_categories(chat_id)

    # 2. لازم ترجع رد لتلغرام
    return jsonify({"ok": True})

# 3. هادي باش يخدم في Render
if _name_ == '_main_':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
