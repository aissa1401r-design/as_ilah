َimport os
import requests
from flask import Flask, request
from supabase import create_client, Client

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

user_state = {}

questions = [
    {"q": "كم عدد أركان الاسلام؟", "options": ["3", "4", "5", "6"], "a": "5"},
    {"q": "ما هي اول سورة في القرآن؟", "options": ["البقرة", "الفاتحة", "الناس", "الاخلاص"], "a": "الفاتحة"},
]

def send_message(chat_id, text, keyboard=None):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(url, json=payload, timeout=5)

def make_inline_keyboard(options):
    keyboard = []
    for opt in options: keyboard.append([{"text": opt, "callback_data": opt}])
    return {"inline_keyboard": keyboard}

def get_or_create_user(chat_id, username): # عدلنا الدالة
    data = supabase.table("users").select("score").eq("chat_id", chat_id).execute()
    if data.data:
        # اذا لقيناه نحدثو الاسم تاعو بالاك تبدل
        supabase.table("users").update({"username": username}).eq("chat_id", chat_id).execute()
        return data.data[0]['score']
    else:
        # اذا جديد ننشأوه بالاسم
        supabase.table("users").insert({"chat_id": chat_id, "username": username, "score": 0}).execute()
        return 0

def update_user_score(chat_id, new_score):
    supabase.table("users").update({"score": new_score}).eq("chat_id", chat_id).execute()

def get_leaderboard():
    # ضرك نجيبو الاسم تاني
    data = supabase.table("users").select("username, score").order("score", desc=True).limit(10).execute()
    return data.data

main_keyboard = {
    "keyboard": [["📖 ابدأ الاختبار"], ["🏆 النتيجة"], ["📊 جدول الترتيب"]],
    "resize_keyboard": True
}

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}

    if "callback_query" in data:
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        answer = data["callback_query"]["data"]
        current_q = user_state.get(chat_id)
        if current_q is None: return "ok", 200

        score = get_or_create_user(chat_id, "unknown") # نجيبو النقاط
        correct_answer = questions[current_q]["a"]

        if answer == correct_answer:
            score += 1
            update_user_score(chat_id, score)
            send_message(chat_id, f"✅ صحيح! +1 نقطة \nنقاطك: *{score}*")
        else:
            send_message(chat_id, f"❌ خطأ. الاجابة: *{correct_answer}*")

        next_q = current_q + 1
        if next_q < len(questions):
            user_state[chat_id] = next_q
            q = questions[next_q]
            kb = make_inline_keyboard(q["options"])
            send_message(chat_id, f"السؤال {next_q+1}/{len(questions)}: {q['q']}", kb)
        else:
            user_state[chat_id] = None
            send_message(chat_id, f"كملت! نقاطك النهائية: *{score}*", main_keyboard)
        return "ok", 200

    if "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    # 1. نجيبو اسم المستخدم من تيليغرام
    username = data["message"]["from"].get("first_name", "مستخدم")
    text = data["message"].get("text", "")

    if text == "/start":
        score = get_or_create_user(chat_id, username) # نبعثو الاسم
        send_message(chat_id, f"مرحبا *{username}*! نقاطك: *{score}*", main_keyboard)

    elif text == "📖 ابدأ الاختبار":
        update_user_score(chat_id, 0)
        user_state[chat_id] = 0
        q = questions[0]
        kb = make_inline_keyboard(q["options"])
        send_message(chat_id, f"السؤال 1/{len(questions)}: {q['q']}", kb)

    elif text == "🏆 النتيجة":
        score = get_or_create_user(chat_id, username)
        send_message(chat_id, f"*{username}* نقاطك: *{score}*", main_keyboard)
    elif text == "📊 جدول الترتيب":
        leaderboard = get_leaderboard()
        text = "*🏆 Top 10 اللاعبين 🏆*\n\n"
        if not leaderboard:
            text = "مازال ما كاين حتى لاعب"
        else:
            for i, player in enumerate(leaderboard, 1):
                name = player['username'] or "مجهول" # اذا ما عندوش اسم
                text += f"*{i}.* {name} - النقاط: *{player['score']}*\n"
        send_message(chat_id, text, main_keyboard)

    return "ok", 200

@app.get("/")
def health_check(): return "Bot is running", 200
