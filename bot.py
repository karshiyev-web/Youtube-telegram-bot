import os
import sqlite3
from flask import Flask
from threading import Thread
from telebot import TeleBot, types

# --- ASOSIY SOZLAMALAR (SIZNING MA'LUMOTLARINGIZ) ---
BOT_TOKEN = "8827072789:AAHaton57wWRfklLLflztam5I35AxjoAozI"
ADMIN_ID = 6759476991
# Majburiy kanal usernamesini yozing (boshiga @ bilan). Agar kerak bo'lmasa [] qoldiring.
CHANNELS = ["@Mega_KinoHd"] 

bot = TeleBot(BOT_TOKEN)
app = Flask('')

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT,
            title TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- WEB SERVER (RENDER UCHUN) ---
@app.route('/')
def home():
    return "Universal Kino Bot Aktiv!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- MAJBURIY OBUNANI TEKSHIRISH ---
def check_sub(user_id):
    if not CHANNELS:
        return True
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']:
                return False
        except Exception:
            pass
    return True

def get_sub_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        url = f"https://t.me{channel.replace('@', '')}"
        keyboard.add(types.InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=url))
    keyboard.add(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return keyboard

# --- BOT BUYRUQLARI ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not check_sub(user_id):
        bot.send_message(
            message.chat.id, 
            "⚠️ Botdan foydalanish uchun homiy kanallarimizga a'zo bo'lishingiz shart!", 
            reply_markup=get_sub_keyboard()
        )
        return

    welcome_text = (
        "👋 **Universal Kino Botga xush kelibsiz!**\n\n"
        "🔍 Kinolarni topish uchun:\n"
        "1️⃣ Kino **kodini** yuboring (masalan: `105`)\n"
        "2️⃣ Kino **nomini** yozib yuboring (masalan: `O'rgimchak odam`)"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_callback(call):
    if check_sub(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id, 
            "🎉 Rahmat! Obuna tasdiqlandi. Endi kino kodini yoki nomini yuborishingiz mumkin."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)

# Admin uchun kino qo'shish (/add)
@bot.message_handler(commands=['add'])
def add_movie_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "🔢 Yangi kino uchun **unikal kod** kiriting (masalan: 550):")
    bot.register_next_step_handler(msg, process_code)

def process_code(message):
    movie_code = message.text.strip()
    msg = bot.reply_to(message, f"🎬 Kino videosini yuboring (Kod: {movie_code}):")
    bot.register_next_step_handler(msg, process_video, movie_code)

def process_video(message, movie_code):
    if message.content_type != 'video':
        bot.reply_to(message, "❌ Xatolik! Faqat video fayl yuborishingiz kerak. Bekor qilindi.")
        return

    file_id = message.video.file_id
    title = message.caption.strip() if message.caption else "Nomsiz kino"

    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", 
                   (movie_code, file_id, title))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ Muvaffaqiyatli saqlandi!\n🔑 Kod: `{movie_code}`\n📝 Nomi: {title}", parse_mode="Markdown")

# Qidiruv tizimi
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    if not check_sub(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=get_sub_keyboard())
        return

    query = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT file_id, title, code FROM movies WHERE code = ?", (query,))
    result = cursor.fetchone()
    
    if not result:
        cursor.execute("SELECT file_id, title, code FROM movies WHERE title LIKE ?", (f"%{query}%",))
        result = cursor.fetchone()
        
    conn.close()

    if result:
        file_id, title, code = result
        bot.send_video(
            message.chat.id, 
            file_id, 
            caption=f"🎬 **Kino nomi:** {title}\n🔑 **Kino kodi:** `{code}`", 
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "🔍 Afsuski, bunday kod yoki nom bilan kino topilmadi. Qayta urinib ko'ring.")

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling()
  
