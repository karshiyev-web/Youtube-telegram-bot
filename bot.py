import os
import sqlite3
from flask import Flask
from threading import Thread
from telebot import TeleBot, types

# --- ASOSIY SOZLAMALAR ---
BOT_TOKEN = "8827072789:AAHaton57wWRfklLLflztam5I35AxjoAozI"
ADMIN_ID = 6759476991
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"Database error: {e}")

# --- WEB SERVER ---
@app.route('/')
def home():
    return "Bot faol!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- MAJBURIY OBUNA ---
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

# --- KLAVIATURALAR ---
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Kino qidirish", "💰 Donat bo'limi")
    if user_id == ADMIN_ID:
        markup.row("⚙️ Admin Panel")
    return markup

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Xabar tarqatish", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("➕ Kino qo'shish", callback_data="admin_add"),
        types.InlineKeyboardButton("✏️ Kinoni tahrirlash", callback_data="admin_edit"),
        types.InlineKeyboardButton("❌ Kinoni o'chirish", callback_data="admin_delete"),
        types.InlineKeyboardButton("❌ Menyuni yopish", callback_data="admin_close")
    )
    return markup

# --- BOT BUYRUQLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    try:
        conn = sqlite3.connect("universal_movies.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    if not check_sub(user_id):
        bot.send_message(
            message.chat.id, 
            "⚠️ Botdan foydalanish uchun homiy kanallarimizga a'zo bo'lishingiz shart!", 
            reply_markup=get_sub_keyboard()
        )
        return

    welcome_text = "👋 **Professional Kino Botga xush kelibsiz!**\n\n🎬 Pastdagi tugmalar orqali botdan to'liq foydalanishingiz mumkin."
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_callback(call):
    if check_sub(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(
            call.message.chat.id, 
            "🎉 Rahmat! Obuna tasdiqlandi. Quyidagi menyudan foydalaning:",
            reply_markup=get_main_keyboard(call.from_user.id)
        )
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali kanalimizga a'zo bo'lmadingiz!", show_alert=True)

# --- ADMIN PANEL CALLBACKS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "admin_stats":
        conn = sqlite3.connect("universal_movies.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM movies")
        total_movies = cursor.fetchone()
        conn.close()
        
        stats_text = f"📊 **Bot statistikasi:**\n\n👤 Jami a'zolar: `{total_users}` ta\n🎬 Bazadagi kinolar: `{total_movies}` ta"
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")

    elif call.data == "admin_add":
        msg = bot.send_message(call.message.chat.id, "🔢 Yangi kino uchun **unikal kod** kiriting (masalan: 120):")
        bot.register_next_step_handler(msg, process_code)

    elif call.data == "admin_edit":
        msg = bot.send_message(call.message.chat.id, "✏️ Tahrirlamoqchi bo'lgan kino **kodini** kiriting:")
        bot.register_next_step_handler(msg, process_edit_code)

    elif call.data == "admin_delete":
        msg = bot.send_message(call.message.chat.id, "❌ O'chirmoqchi bo'lgan kino **kodini** kiriting:")
        bot.register_next_step_handler(msg, process_delete_code)

    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (Matn, rasm yoki video):")
        bot.register_next_step_handler(msg, process_broadcast)
        
    elif call.data == "admin_close":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    bot.answer_callback_query(call.id)

# --- ADMIN STEPS ---
def process_code(message):
    movie_code = message.text.strip()
    msg = bot.reply_to(message, f"🎬 Kino videosini yuboring (Kod: {movie_code}):")
    bot.register_next_step_handler(msg, process_video, movie_code)

def process_video(message, movie_code):
    if message.content_type != 'video':
        bot.reply_to(message, "❌ Xatolik! Faqat video yuborish kerak. Bekor qilindi.")
        return
    file_id = message.video.file_id
    title = message.caption.strip() if message.caption else "Nomsiz kino"

    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", (movie_code, file_id, title))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kod: `{movie_code}`\n📝 Nomi: {title}", parse_mode="Markdown")

def process_edit_code(message):
    movie_code = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM movies WHERE code = ?", (movie_code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        msg = bot.reply_to(message, f"📝 Kino hozirgi nomi: *{result}*\n\nYangi nom (tavsif) kiriting:")
        bot.register_next_step_handler(msg, process_edit_title, movie_code)
    else:
        bot.reply_to(message, "❌ Bunday kodli kino topilmadi.")

def process_edit_title(message, movie_code):
    new_title = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE movies SET title = ? WHERE code = ?", (new_title, movie_code))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Kino nomi muvaffaqiyatli o'zgartirildi!\n🔑 Kod: `{movie_code}`\n📝 Yangi nomi: {new_title}", parse_mode="Markdown")

def process_delete_code(message):
    movie_code = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM movies WHERE code = ?", (movie_code,))
    result = cursor.fetchone()
    
    if result:
        cursor.execute("DELETE FROM movies WHERE code = ?", (movie_code,))
        conn.commit()
        bot.reply_to(message, f"❌ `{result}` nomi ostidagi kino bazadan butkul o'chirildi.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Bunday kodli kino topilmadi.")
    conn.close()

def process_broadcast(message):
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    bot.send_message(message.chat.id, f"🚀 Xabar tarqatish boshlandi... (Jami: {len(users)} ta odam)")
    
    for user in users:
        try:
            bot.copy_message(user[0], message.chat.id, message.message_id)
            success += 1
        except Exception:
            pass
            
    bot.send_message(message.chat.id, f"✅ Xabar tarqatish yakunlandi!\n👥 Qabul qildi: {success} ta foydalanuvchi.")

# --- FOYDALANUVCHILAR UCHUN QIDIRUV TIZIMI ---
@bot.message_handler(func=lambda message: True)
def handle_texts(message):
    user_id = message.from_user.id
    if not check_sub(user_id):
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'ling:", reply_markup=get_sub_keyboard())
        return

    text = message.text.strip()

    if text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "🎛 **Admin boshqaruv paneli:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
        return

    elif text == "🔍 Kino qidirish":
        bot.send_message(message.chat.id, "🔍 Menga kino **kodini** (masalan: 102) yoki kino **nomini** yozib yuboring:")
        return

    elif text == "💰 Donat bo'limi":

