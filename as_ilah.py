import os
import requests
from flask import Flask, request
import random

app = Flask(__name__) # صلحتها ليك

TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_scores = {}
user_state = {} # ضرك تولي: "menu" او {"mode": "quiz", "score": 0}

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def send_message(chat_id, text, keyboard=None):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard: payload["reply_markup"] = keyboard
    requests.post(url, json=payload, timeout=5)

main_keyboard = {"keyboard": [["📖 ابدأ الاختبار"], ["🏆 الترتيب"], ["❓ مساعدة"]], "resize_keyboard": True}
quiz_keyboard = {"keyboard": [["❌ تخطي السؤال"], ["⛔ ايقاف الاختبار"]], "resize_keyboard": True}

def make_options_keyboard(options):
    keyboard = [[{"text": opt}] for opt in options] # كل خيار في سطر
    keyboard.append([{"text": "❌ تخطي السؤال"}, {"text": "⛔ ايقاف الاختبار"}])
    return {"keyboard": keyboard, "resize_keyboard": True}

# 1. نجيبو سؤال عشوائي مازال ما تسألش
def get_random_question():
    url = f"{SUPABASE_URL}/rest/v1/questions?asked=is.false&limit=1"
    res = requests.get(url, headers=HEADERS).json()
    return res[0] if res else None

# 2. نعلمو السؤال بلي تسأل
def mark_as_asked(q_id):
    url = f"{SUPABASE_URL}/rest/v1/questions?id=eq.{q_id}"
    requests.patch(url, headers=HEADERS, json={"asked": True})

# 3. نعلمو اذا الجواب صحيح
def mark_correct(q_id, is_correct):
    url = f"{SUPABASE_URL}/rest/v1/questions?id=eq.{q_id}"
    requests.patch(url, headers=HEADERS, json={"answered_correctly": is_correct})

# 4. نصفر الاختبار
def reset_quiz():
    url = f"{SUPABASE_URL}/rest/v1/questions"
    requests.patch(url, headers=HEADERS, json={"asked": False, "answered_correctly": None})

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}
    if "message" not in data: return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if chat_id not in user_state: user_state[chat_id] = "menu"

    # --- القائمة الرئيسية ---
    if text == "/start" or text == "🏠 القائمة الرئيسية":
        send_message(chat_id, f"مرحبا! نقاطك: {user_scores.get(chat_id, 0)}", main_keyboard)
        user_state[chat_id] = "menu"

    # --- بدء الاختبار ---
    elif text == "📖 ابدأ الاختبار":
        reset_quiz() # صفر الاختبار القديم
        user_state[chat_id] = {"mode": "quiz", "score": 0}
        send_next_question(chat_id)

    # --- ايقاف الاختبار ---
    elif text == "⛔ ايقاف الاختبار":
        if isinstance(user_state[chat_id], dict):
            score = user_state[chat_id]["score"]
            # حسب كم سؤال جاوب
            res = requests.get(f"{SUPABASE_URL}/rest/v1/questions?asked=is.true&select=id", headers=HEADERS).json()
            total = len(res)
            send_message(chat_id, f"انتهى الاختبار! ✅\nنقاطك: {score} / {total}", main_keyboard)
            user_state[chat_id] = "menu"
            user_scores[chat_id] = score # حفظ النقطة النهائية

    # --- منطق الاجابة ---
    # --- منطق الاجابة ---
    elif isinstance(user_state.get(chat_id), dict) and user_state[chat_id].get("mode") == "quiz":

        q_id = user_state[chat_id].get("current_q")
        if not q_id:
            send_message(chat_id, "استنى شوية... نجيبلك سؤال جديد", main_keyboard)
            send_next_question(chat_id)
            return "ok", 200

        # 1. حالة التخطي
        if text == "❌ تخطي السؤال":
            q = get_question_by_id(q_id)
            if q:
                mark_correct(q_id, False) # نعتبرو تخطي = خطأ
                send_message(chat_id, f"تم التخطي. الاجابة: {q['correct_answer']}", quiz_keyboard)
            user_state[chat_id]["current_q"] = None # نفرغو باش مايعاودوش
            send_next_question(chat_id) # نبعثو الجديد
            return "ok", 200

        # 2. حالة الايقاف
        if text == "⛔ ايقاف الاختبار":
            stop_quiz(chat_id)
            return "ok", 200

        # 3. حالة الاجابة العادية
        q = get_question_by_id(q_id)
        if not q:
            send_next_question(chat_id)
            return "ok", 200
            
        is_correct = (text == q["correct_answer"])
        mark_correct(q_id, is_correct)
        user_state[chat_id]["current_q"] = None # نفرغو بعد ما نجاوب

        if is_correct:
            user_state[chat_id]["score"] += 1
            send_message(chat_id, f"✅ صحيح! +1 نقطة", quiz_keyboard)
        else:
            send_message(chat_id, f"❌ خطأ. الاجابة: {q['correct_answer']}", quiz_keyboard)

        send_next_question(chat_id) # نبعثو اللي بعدو

def send_next_question(chat_id):
    q = get_random_question()
    if not q: # كملو الاسئلة
        stop_quiz(chat_id)
        return

    mark_as_asked(q["id"]) # 1. علمو بلي تسأل لول
    user_state[chat_id]["current_q"] = q["id"] # 2. خزنو ضرك
    
    options = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
    random.shuffle(options) # نخلطوهم
    kb = make_options_keyboard(options)
    send_message(chat_id, f"السؤال: {q['question']}", kb)

def get_question_by_id(q_id):
    url = f"{SUPABASE_URL}/rest/v1/questions?id=eq.{q_id}&select=*"
    return requests.get(url, headers=HEADERS).json()[0]

def stop_quiz(chat_id): # كي يكملو الاسئلة
    score = user_state[chat_id]["score"]
    res = requests.get(f"{SUPABASE_URL}/rest/v1/questions?asked=is.true&select=id", headers=HEADERS).json()
    total = len(res)
    send_message(chat_id, f"كملنا كل الاسئلة! ✅\nنقاطك النهائية: {score} / {total}", main_keyboard)
    user_state[chat_id] = "menu"

@app.get("/")
def health_check():
    return "Bot is running", 200
