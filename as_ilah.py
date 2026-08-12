import os
import requests
from flask import Flask, request
from supabase import create_client, Client

app = Flask(name)

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

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        user = get_user(chat_id)

        if not user:
            create_user(chat_id)
            user = get_user(chat_id) # تعديل مهم باش مايطيحش
            send_message(chat_id, "مرحبا بيك في بوت الاسئلة الدينية 🌙")

        if text == "/start":
            reset_user(chat_id)
            send_categories(chat_id)
            return "ok"

        elif text == "سؤال جديد":
            send_question(chat_id)

        elif text == "/profile":
            user = get_user(chat_id)
            points = user['points']; level = user['level']
            remaining = (level * 60) - points
            send_message(chat_id, f"📊 <b>ملفك</b>\nالمستوى: {level}\nالنقاط: {points}\nباقيلك {remaining} نقطة للمستوى الجاي")

        elif text == "/top":
            res = supabase.table("users").select("*").order("points", desc=True).limit(10).execute()
            msg = "🏆 <b>افضل 10:</b>\n" + "\n".join([f"{i}. {u['points']} نقطة" for i,u in enumerate(res.data,1)])
            send_message(chat_id, msg)

    elif "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        message_id = update["callback_query"]["message"]["message_id"]
        data = update["callback_query"]["data"]
        answer_callback(update["callback_query"]["id"])
        user = get_user(chat_id)

        if data.startswith("cat_"):
            cat_id = int(data.split("_")[1])
            supabase.table("users").update({"current_category": cat_id}).eq("chat_id", chat_id).execute()
            reset_user(chat_id)
            send_message(chat_id, "✅ تم اختيار القسم. نبداو 👇")
            send_question(chat_id)

        elif data.startswith("answer_"):
            edit_buttons(chat_id, message_id)
            parts = data.split("_", 2)
            question_id = int(parts[1])
            user_answer = parts[2]

            question = get_question_by_id(question_id)
            if not question: return "ok", 200
            correct = question['correct_answer']
            explanation = question.get('explanation', 'مافيهش شرح لهذا السؤال')

            if user_answer.strip() == correct.strip():
                new_points = user['points'] + 10; new_level = user['level']
                msg = f"✅ <b>صحيح!</b> +10 نقاط\nالمجموع: {new_points}\n\n💡 <b>الشرح:</b> {explanation}"
                if new_points >= new_level * 60:
                    new_level += 1
                    msg = f"🎉 <b>مبروك! طلعت للمستوى {new_level}</b>\n\n" + msg
                supabase.table("users").update({"points": new_points, "level": new_level}).eq("chat_id", chat_id).execute()
                send_message(chat_id, msg)
            else:
                msg = f"❌ <b>خطأ!</b>\nالصحيح هو: <b>{correct}</b>\n\n💡 <b>الشرح:</b> {explanation}"
                send_message(chat_id, msg)

            send_question(chat_id)

        elif data == "choose_category":
            send_categories(chat_id)
        elif data == "confirm_reset":
            reset_user(chat_id)
            send_message(chat_id, "✅ تمت اعادة القسم\nنبداو من جديد 👇")
            send_question(chat_id)

    return "ok", 200

@app.route("/")
def home():
    return "Bot is running!", 200

if name == 'main':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
