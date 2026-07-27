import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_scores = {}
user_state = {}

# ضرك كل سؤال فيه 4 اختيارات و الاجابة الصحيحة
questions = [
    {"q": "كم عدد أركان الاسلام؟", "options": ["3", "4", "5", "6"], "a": "5"},
    {"q": "ما هي اول سورة في القرآن؟", "options": ["البقرة", "الفاتحة", "الناس", "الاخلاص"], "a": "الفاتحة"},
    {"q": "كم عدد الصلوات في اليوم؟", "options": ["3", "4", "5", "6"], "a": "5"},
    {"q": "من هو اول الانبياء؟", "options": ["نوح", "ادم", "ابراهيم", "موسى"], "a": "ادم"},
    {"q": "في اي شهر نزل القرآن؟", "options": ["شعبان", "رمضان", "رجب", "محرم"], "a": "رمضان"},
    {"q": "كم عدد سور القرآن الكريم؟", "options": ["100", "114", "120", "99"], "a": "114"},
    {"q": "ما هو الركن الخامس من الاسلام؟", "options": ["الصلاة", "الزكاة", "الصوم", "الحج"], "a": "الحج"},
    {"q": "من هو خاتم الانبياء؟", "options": ["عيسى", "موسى", "محمد", "ابراهيم"], "a": "محمد"},
    {"q": "كم عدد ايام عيد الفطر؟", "options": ["1", "3", "7", "10"], "a": "1"},
    {"q": "ما هي القبلة الاولى للمسلمين؟", "options": ["المسجد الحرام", "المسجد النبوي", "المسجد الاقصى", "مسجد قباء"], "a": "المسجد الاقصى"}
]

def send_message(chat_id, text, keyboard=None):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    requests.post(url, json=payload, timeout=5)

main_keyboard = {
    "keyboard": [["📖 ابدأ الاختبار"], ["🏆 النتيجة"], ["❓ مساعدة"]],
    "resize_keyboard": True
}

def make_options_keyboard(options):
    # نحول الاختيارات لازرار. كل 2 في سطر
    keyboard = []
    row = []
    for opt in options:
        row.append(opt)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append(["❌ تخطي السؤال"]) # زر تخطي
    return {"keyboard": keyboard, "resize_keyboard": True}

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
        user_state[chat_id] = 0
        q = questions[0]
        kb = make_options_keyboard(q["options"])
        send_message(chat_id, f"السؤال 1/10: {q['q']}", kb)

    elif text == "🏆 النتيجة":
        send_message(chat_id, f"نقاطك: {user_scores[chat_id]} من {len(questions)}", main_keyboard)

    elif text == "❌ تخطي السؤال":
        current_q = user_state[chat_id]
        if current_q is not None:
            send_message(chat_id, f"تم التخطي. الاجابة: {questions[current_q]['a']}", main_keyboard)
            next_q = current_q + 1
            if next_q < len(questions):
                user_state[chat_id] = next_q
                q = questions[next_q]
                kb = make_options_keyboard(q["options"])
                send_message(chat_id, f"السؤال {next_q+1}/10: {q['q']}", kb)
            else:
                user_state[chat_id] = None
                send_message(chat_id, f"كملت! نقاطك: {user_scores[chat_id]}", main_keyboard)

    else: # هنا يشيك الاجابة
        current_q = user_state[chat_id]
        if current_q is not None:
            correct_answer = questions[current_q]["a"]
            if text == correct_answer: # ضرك يقارن مباشرة لانها من الازرار
                user_scores[chat_id] += 1
                send_message(chat_id, "✅ صحيح! +1 نقطة", main_keyboard)
            else:
                send_message(chat_id, f"❌ خطأ. الاجابة: {correct_answer}", main_keyboard)

            next_q = current_q + 1
            if next_q < len(questions):
                user_state[chat_id] = next_q
                q = questions[next_q]
                kb = make_options_keyboard(q["options"])
                send_message(chat_id, f"السؤال {next_q+1}/10: {q['q']}", kb)
            else:
                user_state[chat_id] = None
                send_message(chat_id, f"كملت الاختبار! نقاطك النهائية: {user_scores[chat_id]}/10", main_keyboard)
        else:
            send_message(chat_id, "اختار من الازرار 👇", main_keyboard)

    return "ok", 200

@app.get("/")
def health_check():
    return "Bot is running", 200
                
