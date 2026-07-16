import os
import asyncio
import sqlite3
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- ASOSIY SOZLAMALAR ---
BOT_TOKEN = "8827072789:AAHaton57wWRfklLLflztam5I35AxjoAozI"
ADMIN_ID = 6759476991
CHANNELS = ["@Mega_KinoHd"]  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask('')

# --- ADMIN HOLATLARI (FSM) ---
class AdminStates(StatesGroup):
    waiting_for_movie_code = State()
    waiting_for_movie_video = State()
    waiting_for_broadcast_msg = State()
    waiting_for_delete_code = State()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT, title TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- WEB SERVER ---
@app.route('/')
def home():
    return "Professional Kino Bot 100% Aktiv!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- MAJBURIY OBUNA TEKSHIRISH ---
async def check_sub(user_id: int) -> bool:
    if not CHANNELS:
        return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

# --- KLAVIATURALAR ---
def get_main_keyboard(user_id: int):
    buttons = [[KeyboardButton(text="🔍 Kino qidirish"), KeyboardButton(text="💰 Donat bo'limi")]]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_sub_keyboard():
    buttons = []
    for channel in CHANNELS:
        url = f"https://t.me{channel.replace('@', '')}"
        buttons.append([InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=url)])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    buttons = [
        [InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="adm_add"), InlineKeyboardButton(text="❌ Kinoni o'chirish", callback_data="adm_del")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"), InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="adm_send")],
        [InlineKeyboardButton(text="❌ Menyuni yopish", callback_data="adm_close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- BOT BUYRUQLARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

    if not await check_sub(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun homiy kanallarimizga a'zo bo'lishingiz shart!", reply_markup=get_sub_keyboard())
        return

    await message.answer("👋 **Udar Kino Botga xush kelibsiz!**\n\n🎬 Pastdagi tugmalar yoki to'g'ridan-to'g'ri **kino kodini** yuborib qidirishingiz mumkin.", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

# --- INLINE HANDLER ---
@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        try:
            await call.message.delete()
        except:
            pass
        await call.message.answer("🎉 Rahmat! Obuna tasdiqlandi.", reply_markup=get_main_keyboard(call.from_user.id))
    else:
        await call.answer("❌ Siz hali kanalimizga a'zo bo'lmadingiz!", show_alert=True)

# --- ADMIN PANEL CALLBACKS ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_callbacks(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "adm_stats":
        conn = sqlite3.connect("universal_movies.db")
        cursor = conn.cursor()
        u_res = cursor.execute("SELECT COUNT(*) FROM users").fetchone()
        m_res = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()
        conn.close()
        u_count = u_res[0] if u_res else 0
        m_count = m_res[0] if m_res else 0
        await call.message.answer(f"📊 **Bot statistikasi:**\n\n👤 Jami a'zolar: `{u_count}` ta\n🎬 Bazadagi kinolar: `{m_count}` ta", parse_mode="Markdown")
    
    elif call.data == "adm_add":
        await call.message.answer("🔢 Yangi kino uchun **unikal kod** kiriting (masalan: 550):")
        await state.set_state(AdminStates.waiting_for_movie_code)

    elif call.data == "adm_del":
        await call.message.answer("❌ O'chirmoqchi bo'lgan kino **kodini** kiriting:")
        await state.set_state(AdminStates.waiting_for_delete_code)

    elif call.data == "adm_send":
        await call.message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabarni (reklamani) kiriting:")
        await state.set_state(AdminStates.waiting_for_broadcast_msg)

    elif call.data == "adm_close":
        try:
            await call.message.delete()
        except:
            pass
    
    await call.answer()

# --- ADMIN PROCESSES (FSM) ---
@dp.message(AdminStates.waiting_for_movie_code)
async def process_movie_code(message: types.Message, state: FSMContext):
    await state.update_data(m_code=message.text.strip())
    await message.answer("🎬 Endi esa kinoning **videosini** yuboring (caption qismiga nomini yozishingiz mumkin):")
    await state.set_state(AdminStates.waiting_for_movie_video)

@dp.message(AdminStates.waiting_for_movie_video, F.video)
async def process_movie_video(message: types.Message, state: FSMContext):
    data = await state.get_data()
    movie_code = data['m_code']
    file_id = message.video.file_id
    title = message.caption.strip() if message.caption else "Nomsiz kino"

    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", (movie_code, file_id, title))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kod: `{movie_code}`\n📝 Nomi: {title}", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.waiting_for_delete_code)
async def process_delete_movie(message: types.Message, state: FSMContext):
    code = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    changes = conn.total_changes
    conn.commit()
    conn.close()

    if changes > 0:
        await message.answer(f"❌ `{code}` kodli kino bazadan butkul o'chirildi.")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")
    await state.clear()

@dp.message(AdminStates.waiting_for_broadcast_msg)
async def process_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 Reklama tarqatish boshlandi...")
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    users = cursor.execute("SELECT user_id FROM users").fetchall()
    conn.close()

    success = 0
    for user in users:
        try:
            await bot.copy_message(chat_id=user[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            await asyncio.sleep(0.05)  
        except Exception:
            pass
    await message.answer(f"✅ Reklama yakunlandi.\n👥 Muvaffaqiyatli yuborildi: {success} ta odamga.")
    await state.clear()

# --- KINO QIDIRISH VA MATNLAR ---
@dp.message(F.text)
async def handle_text_and_search(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_sub(user_id):
        await message.answer("⚠️ Avval kanalga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

    if message.text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        await message.answer("⚙️ Admin panelga xush kelibsiz:", reply_markup=get_admin_keyboard())
        return
    elif message.text == "🔍 Kino qidirish":
        await message.answer("🔢 Kino kodini yuboring (Masalan: 120):")
        return
    elif message.text == "💰 Donat bo'limi":
        await message.answer("💰 Bizni qo'llab-quvvatlaganingiz uchun rahmat!")
        return

    movie_code = message.text.strip()
    conn = sqlite3.connect("universal_movies.db")
    cursor = conn.cursor()
    result = cursor.execute("SELECT file_id, title FROM movies WHERE code = ?", (movie_code,)).fetchone()
    conn.close()

    if result:
        file_id, title = result
        await bot.send_video(chat_id=message.chat.id, video=file_id, caption=f"🎬 **Kino nomi:** {title}\n🔑 **Kod:** {movie_code}", parse_mode="Markdown")
    else:
        await message.answer("❌ Afsuski, bunday kodli kino topilmadi. Kodni to'g'ri yozganingizni tekshiring.")

# --- INLINE START ---
async def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("Bot Renderda muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())

