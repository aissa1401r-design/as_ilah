import os
import requests
from flask import Flask, request
import random

app = Flask(__name__) # صلحتها

TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL") # زيدهم في Render
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # زيدهم في Render
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_scores = {}
user_state = {}

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

# حذفنا قائمة الاسئلة. ضرك نجيبوها من Supabase

def send_message(chat_id, text, keyboard=None):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        payload["reply_markup"] = keyboard
    requests.post(url, json=payload, timeout=5)

main_keyboard = {
    "keyboard": [["📖 ابدأ الاختبار"], ["🏆 الترتيب"], ["❓ مساعدة"]], # بدلنا النتيجة بالترتيب
    "resize_keyboard": True
}

def make_options_keyboard(options):
    keyboard = []
    row = []
    for opt in options:
        row.append({"text": opt}) # لازم dict باش يخدم مع Inline
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([{"text": "❌ تخطي السؤال"}])
    return {"keyboard": keyboard, "resize_keyboard": True}

# جديدة: نجيبو سؤال عشوائي من Supabase
def get_random_question():
    url = f"{SUPABASE_URL}/rest/v1/questions?select=*"
    res = requests.get(url, headers=HEADERS).json()
    return random.choice(res)

# جديدة: نجيبو سؤال بالـ id
def get_question_by_id(q_id):
    url = f"{SUPABASE_URL}/rest/v1/questions?id=eq.{q_id}&select=*"
    res = requests.get(url, headers=HEADERS).json()
    return res[0]

# جديدة: الترتيب
def get_leaderboard():
    sorted_players = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    text = "*ترتيب اللاعبين:*\n\n"
    for i, (chat_id, score) in enumerate(sorted_players[:10], 1):
        text += f"{i}. اللاعب {chat_id} - {score} نقطة\n"
    return text

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}
    if "message" not in data: return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if chat_id not in user_scores:
        user_scores[chat_id] = 0
        user_state[chat_id] = None

    if text == "/start":
        send_message(chat_id, f"مرحبا! نقاطك: {user_scores[chat_id]}", main_keyboard)

    elif text == "📖 ابدأ الاختبار":
        q = get_random_question()
        user_state[chat_id] = q["id"] # نخزنو id السؤال مش الرقم
        kb = make_options_keyboard([q["option_a"], q["option_b"], q["option_c"], q["option_d"]])
        send_message(chat_id, f"السؤال: {q['question']}", kb)

    elif text == "🏆 الترتيب": # بدلنا النتيجة
        send_message(chat_id, get_leaderboard(), main_keyboard)

    elif text == "❌ تخطي السؤال":
        current_q_id = user_state[chat_id]
        if current_q_id:
            q = get_question_by_id(current_q_id)
            send_message(chat_id, f"تم التخطي. الاجابة: {q['correct_answer']}", main_keyboard)
            user_state[chat_id] = None
            # نبعثو سؤال جديد
            q = get_random_question()
            user_state[chat_id] = q["id"]
            kb = make_options_keyboard([q["option_a"], q["option_b"], q["option_c"], q["option_d"]])
            send_message(chat_id, f"السؤال الجديد: {q['question']}", kb)

    else: # هنا يشيك الاجابة
        current_q_id = user_state[chat_id]
        if current_q_id:
            q = get_question_by_id(current_q_id)
            correct_answer = q["correct_answer"]
            if text == correct_answer:
                user_scores[chat_id] += 1
                send_message(chat_id, f"✅ صحيح! +1 نقطة. مجموعك: {user_scores[chat_id]}", main_keyboard)
            else:
                send_message(chat_id, f"❌ خطأ. الاجابة: {correct_answer}", main_keyboard)
                
            user_state[chat_id] = None
            # سؤال جديد
            q = get_random_question()
            user_state[chat_id] = q["id"]
            kb = make_options_keyboard([q["option_a"], q["option_b"], q["option_c"], q["option_d"]])
            send_message(chat_id, f"السؤال التالي: {q['question']}", kb)
        else:
            send_message(chat_id, "اختار من الازرار 👇", main_keyboard)

    return "ok", 200

@app.get("/")
def health_check():
    return "Bot is running", 200
