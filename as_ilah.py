from flask import Flask, request
import os
import requests
import random
from supabase import create_client

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

QUESTIONS = [
    {"q": "ما هي عاصمة الجزائر؟", "a": "الجزائر"},
    {"q": "كم عدد ايام الاسبوع؟", "a": "7"},
    {"q": "ما لون السماء؟", "a": "ازرق"},
]

def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{API_URL}/sendMessage", json=data)

def get_user(chat_id):
    res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    if res.data:
        return res.data[0]
    else:
        new_user = {"chat_id": chat_id, "points": 0, "level": 1}
        supabase.table("users").insert(new_user).execute()
        return new_user

def get_level(points):
    return (points // 50) + 1

def points_to_next_level(points):
    current_level_points = (get_level(points) - 1) * 50
    return 50 - (points - current_level_points)

def get_top_players():
    res = supabase.table("users").select("chat_id, points, level").order("points", desc=True).limit(10).execute()
    return res.data

@app.route("/", methods=["POST"]) # <-- التغيير المهم هنا
def webhook():
    data = request.get_json()
    print("DATA:", data)

    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        user = get_user(chat_id)
        current_level = get_level(user['points'])

        if text == "/top":
            top_players = get_top_players()
            msg = "🏆 افضل 10 لاعبين 🏆\n\n"
            for i, player in enumerate(top_players, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                lvl = player.get('level', get_level(player['points']))
                msg += f"{medal} المستوى {lvl} | {player['points']} نقطة\n"
            send_message(chat_id, msg)

        elif text == "/profile":
            remaining = points_to_next_level(user['points'])
            send_message(chat_id, f"👤 الملف الشخصي\nالمستوى: {current_level} 🏆\nالنقاط: {user['points']} ⭐️\nباقيلك: {remaining} نقطة للمستوى {current_level + 1}")

        elif text == "/start":
            question = random.choice(QUESTIONS)
            supabase.table("users").update({"last_answer": question["a"]}).eq("chat_id", chat_id).execute()
            keyboard = {"keyboard": [["سؤال جديد", "/profile", "/top"]], "resize_keyboard": True}
            send_message(chat_id, f"مرحبا! ✅\nالمستوى: {current_level} | نقاطك: {user['points']}\n\nالسؤال: {question['q']}", keyboard)

        elif text == "سؤال جديد":
            question = random.choice(QUESTIONS)
            supabase.table("users").update({"last_answer": question["a"]}).eq("chat_id", chat_id).execute()
            send_message(chat_id, f"السؤال: {question['q']}")

        else:
            correct_answer = user.get("last_answer", "").strip().lower()
            user_answer = text.strip().lower()

            if user_answer == correct_answer and correct_answer!= "":
                new_points = user["points"] + 10
                new_level = get_level(new_points)
                old_level = current_level

                update_data = {"points": new_points, "last_answer": None}
                level_msg = ""
                if new_level > old_level:
                    update_data["level"] = new_level
                    level_msg = f"\n🎉 مبروك وصلت للمستوى {new_level}!"

                supabase.table("users").update(update_data).eq("chat_id", chat_id).execute()
                send_message(chat_id, f"صحيح! +10 نقاط{level_msg} 🎉\nالمستوى: {new_level} | نقاطك: {new_points}")
            else:
                supabase.table("users").update({"last_answer": None}).eq("chat_id", chat_id).execute()
                send_message(chat_id, f"غلط 😅\nالجواب الصحيح: {correct_answer}\nالمستوى: {current_level} | نقاطك: {user['points']}")

            question = random.choice(QUESTIONS)
            supabase.table("users").update({"last_answer": question["a"]}).eq("chat_id", chat_id).execute()
            send_message(chat_id, f"السؤال: {question['q']}")

    return "ok", 200

@app.route("/")
def home():
    return "OK", 200
