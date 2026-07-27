import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
SHOP_NAME = "بوت الأسئلة الدينية"

# 1. هذا وين نخزنو النقاط. يتمسحو كي يعاود يطلع السيرفر
user_scores = {} # مثال: {123456: 3}
user_state = {} # باش نتفكرو في اي سؤال راهو

# 2. الاسئلة
questions = [
    {"q": "كم عدد أركان الاسلام؟", "a": "5"},
    {"q": "ما هي اول سورة في القرآن؟", "a": "الفاتحة"},
    {"q": "كم عدد الصلوات في اليوم؟", "a": "5"},{'q':'ما أعظم ما أمر الله','a':'التوحيد'},{'q':'كم عدد مراتب الدين','a':'3'},{'q':'من أفضل الناس بعد الانبياء','a':'الصحابة'},
    {'q':'ماأعظم الذنوب','a':'الشرك'},{'q':'من أول رسول الى أهل الارض','a':'نوح'},{'q':'ما هو الشيئ الذي يمنع الخلود في النار','a':'التوحيد'},{'q':'كم عدد سور القرآن','a':'114'},
    {'q':'ما هي السورة التي تعدل ثلث القرآن','a':'الاخلاص'},{'q':'من الخليفة الذي جاء يعد رسول الله صلى الله عليه وسلم','a':'أبو بكر'},{'q':'من هو النبي الذي بعث الى اصحاب الايكة','a':'شعيب'},
    {'q':'كيف نسمي الذين يعطلون الله عن صفاته','a':'المعطلة'},{'q':'اين الله','a':'في السماء'},{'q':'من هو الصحابي الذي ذكر باسمه في القرآن','a':'زيد'},
    {'q':'كم عدد اركان الايمان','a':'6'},{'q':'ماهو اعظم الذنوب','a':'الشرك'}
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

@app.post(f"/{TOKEN}")
def webhook():
    data = request.get_json(silent=True) or {}
    if "message" not in data: return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # نجيبو النقاط تاعه ولا نحطو 0
    if chat_id not in user_scores:
        user_scores[chat_id] = 0
        user_state[chat_id] = None

    if text == "/start":
        msg = f"مرحبا بك في {SHOP_NAME}\nالنقاط تاعك: {user_scores[chat_id]}"
        send_message(chat_id, msg, main_keyboard)

    elif text == "📖 ابدأ الاختبار":
        user_state[chat_id] = 0 # نبداو من السؤال 0
        q = questions[0]["q"]
        send_message(chat_id, f"السؤال 1: {q}", main_keyboard)

    elif text == "🏆 النتيجة":
        score = user_scores[chat_id]
        send_message(chat_id, f"نقاطك الحالية: {score} من {len(questions)}", main_keyboard)

    elif text == "❓ مساعدة":
        send_message(chat_id, "اضغط ابدأ الاختبار و جاوب. كل اجابة صحيحة = نقطة", main_keyboard)

    else: # هنا يشيك اذا راهو يجاوب
        current_q = user_state[chat_id]
        if current_q is not None: # معناها راهو في اختبار
            correct_answer = questions[current_q]["a"]
            if text.strip() == correct_answer:
                user_scores[chat_id] += 1
                send_message(chat_id, "✅ صحيح! +1 نقطة", main_keyboard)
            else:
                send_message(chat_id, f"❌ خطأ. الاجابة الصحيحة: {correct_answer}", main_keyboard)

            # نروحو للسؤال الجاي
            next_q = current_q + 1
            if next_q < len(questions):
                user_state[chat_id] = next_q
                send_message(chat_id, f"السؤال {next_q+1}: {questions[next_q]['q']}", main_keyboard)
            else:
                user_state[chat_id] = None
                send_message(chat_id, f"كملت الاختبار! نقاطك: {user_scores[chat_id]}", main_keyboard)
        else:
            send_message(chat_id, "اختار من الازرار تحت 👇", main_keyboard)

    return "ok", 200

@app.get("/")
def health_check():
    return "Bot is running", 200
