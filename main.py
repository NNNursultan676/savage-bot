import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8090093417
GROUP_ID = -1002007015749

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

join_requests = []
approved_users = []
action_log = []

def user_in_group_only(message: types.Message):
    return message.chat.id == GROUP_ID

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Я работаю. Используй /joinlist или /info4leader")

@dp.chat_join_request_handler()
async def handle_join_request(join_request: ChatJoinRequest):
    join_requests.append(join_request)
    await bot.send_message(
        GROUP_ID,
        f"👤 Заявка от: {join_request.from_user.full_name} (@{join_request.from_user.username or 'нет username'})\n"
        f"Чтобы принять, используй /joinlist",
    )

@dp.message_handler(commands=['joinlist'])
async def show_join_list(message: types.Message):
    if not user_in_group_only(message):
        return

    if not join_requests:
        await message.reply("Нет ожидающих заявок.")
        return

    for req in join_requests:
        btn = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Принять", callback_data=f"approve:{req.from_user.id}")
        )
        await message.reply(f"Заявка от: {req.from_user.full_name} (@{req.from_user.username or 'нет username'})", reply_markup=btn)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("approve:"))
async def approve_user(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split(":")[1])
    join_req = next((r for r in join_requests if r.from_user.id == user_id), None)

    if join_req:
        await bot.approve_chat_join_request(GROUP_ID, user_id)
        join_requests.remove(join_req)
        approved_users.append(user_id)
        action_log.append(f"✅ {callback_query.from_user.full_name} одобрил {join_req.from_user.full_name}")
        await callback_query.answer("Пользователь одобрен")
        await bot.send_message(GROUP_ID, f"✅ {join_req.from_user.full_name} принят в группу.")
    else:
        await callback_query.answer("Заявка не найдена", show_alert=True)

@dp.message_handler(commands=['info4leader'])
async def info_for_leader(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только для админа.")
        return

    approved = len(approved_users)
    log_text = "\n".join(action_log[-10:]) or "Нет действий."
    await message.reply(f"📊 Принятых заявок: {approved}\n\n🕓 Последние действия:\n{log_text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
