import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1002007015749
LEADER_ID = 8090093417      

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Middleware: пропускаем сообщения только от группы
class GroupOnlyMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.id != GROUP_ID:
            raise CancelHandler()

dp.middleware.setup(GroupOnlyMiddleware())

# Хранилища
join_requests = []
accepted_users = []
log = []

# Команда: список заявок
@dp.message_handler(commands=['joinlist'])
async def join_list_handler(message: types.Message):
    if not join_requests:
        await message.reply("Нет входящих заявок.")
        return

    for user in join_requests:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user['id']}")
        )
        await message.reply(f"Заявка от {user['username']} (ID: {user['id']})", reply_markup=markup)

# Обработка кнопки "Принять"
@dp.callback_query_handler(lambda c: c.data.startswith('accept_'))
async def accept_callback(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    user = next((u for u in join_requests if u['id'] == user_id), None)

    if not user:
        await callback_query.answer("Заявка не найдена.")
        return

    try:
        await bot.approve_chat_join_request(chat_id=GROUP_ID, user_id=user_id)
        join_requests.remove(user)
        accepted_users.append(user)
        now = (datetime.utcnow() + timedelta(hours=5)).strftime("%d.%m.%Y %H:%M")  # Казахстан (UTC+5)
        log.append(
            f"✅ {callback_query.from_user.username or 'admin'} принял {user['username']} "
            f"(ID: {user['id']}) в {now} по времени KZ"
        )
        await callback_query.answer("Пользователь принят.")
    except Exception as e:
        await callback_query.answer("Ошибка при принятии.")
        logging.error(e)

# Команда: журнал действий
@dp.message_handler(commands=['info4leader'])
async def info_for_leader(message: types.Message):
    if message.from_user.id != LEADER_ID:
        return
    if not log:
        await message.reply("Журнал пуст.")
    else:
        await message.reply("\n".join(log))

# Команда: очистка журнала
@dp.message_handler(commands=['clearlog'])
async def clear_log(message: types.Message):
    if message.from_user.id == LEADER_ID:
        log.clear()
        await message.reply("Журнал очищен.")

# Команда: перезапуск бота (только лидер)
@dp.message_handler(commands=['restart'])
async def restart_bot(message: types.Message):
    if message.from_user.id == LEADER_ID:
        await message.reply("♻️ Перезапуск бота...")
        os._exit(0)

# Обработка входящих заявок
@dp.chat_join_request_handler()
async def handle_join_request(request: types.ChatJoinRequest):
    if any(u['id'] == request.from_user.id for u in join_requests):
        return

    join_requests.append({
        "id": request.from_user.id,
        "username": request.from_user.username or "без ника"
    })
    await bot.send_message(GROUP_ID, f"🆕 Новая заявка от {request.from_user.username or 'без ника'}")

# Обработка /start в личке
@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def private_start(message: types.Message):
    await message.reply("❗ Этот бот работает только внутри группы.")

# Flask-сервер для Render / UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Запуск
if __name__ == '__main__':
    Thread(target=run_flask).start()
    executor.start_polling(dp, skip_updates=True)
