import logging
import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1002007015749
LEADER_ID = 8090093417  # твой Telegram ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Middleware: пропускаем только группу
class GroupOnlyMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.id != GROUP_ID:
            raise CancelHandler()

dp.middleware.setup(GroupOnlyMiddleware())

# Данные
join_requests = []
accepted_users = []
log = []

# Команда /joinlist
@dp.message_handler(commands=['joinlist'])
async def join_list_handler(message: types.Message):
    if not join_requests:
        sent = await message.reply("Нет входящих заявок.")
        await asyncio.sleep(10)
        await sent.delete()
        return

    for user in join_requests:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user['id']}")
        )
        sent = await message.reply(
            f"Заявка от @{user['username']} (ID: {user['id']})", reply_markup=markup)
        await asyncio.sleep(15)
        await sent.delete()

# Обработка кнопки принятия
@dp.callback_query_handler(lambda c: c.data.startswith('accept_'))
async def accept_callback(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    user = next((u for u in join_requests if u['id'] == user_id), None)

    if not user:
        await callback_query.answer("Заявка не найдена.", show_alert=True)
        return

    try:
        await bot.approve_chat_join_request(chat_id=GROUP_ID, user_id=user_id)
        join_requests.remove(user)
        accepted_users.append(user)
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        log.append(f"✅ @{callback_query.from_user.username or 'без ника'} принял @{user['username']} (ID: {user['id']}) в {now}")
        await callback_query.answer("Пользователь принят.")
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        logging.error(e)
        await callback_query.answer("Ошибка при принятии.", show_alert=True)

# Команда /info4leader
@dp.message_handler(commands=['info4leader'])
async def info_for_leader(message: types.Message):
    if message.from_user.id != LEADER_ID:
        return

    if not log:
        await message.reply("Журнал пуст.")
        return

    text = "\n".join(log)
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🗑 Очистить журнал", callback_data="clear_log")
    )
    await message.reply(text, reply_markup=markup)

# Кнопка очистки журнала
@dp.callback_query_handler(lambda c: c.data == "clear_log")
async def clear_log(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != LEADER_ID:
        await callback_query.answer("Нет доступа.")
        return
    log.clear()
    await callback_query.answer("Журнал очищен.")
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

# Обработка входящих заявок
@dp.chat_join_request_handler()
async def handle_join_request(request: types.ChatJoinRequest):
    join_requests.append({
        "id": request.from_user.id,
        "username": request.from_user.username or "без ника"
    })
    await bot.send_message(GROUP_ID, f"🆕 Новая заявка от @{request.from_user.username or 'без ника'}")

# Ответ на /start в личке
@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def private_start(message: types.Message):
    await message.reply("❗ Этот бот работает только внутри группы.")

# Фиктивный сервер для Render
async def hold_port():
    server = await asyncio.start_server(lambda r, w: None, port := int(os.environ.get("PORT", 10000)))
    await server.serve_forever()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(hold_port())  # чтобы Render не выключал
    executor.start_polling(dp, skip_updates=True)
