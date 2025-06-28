import json
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command

import asyncio
from aiohttp import web

API_TOKEN = 'YOUR_BOT_TOKEN'  
ADMIN_ID = 8090093417

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'requests': [], 'log': []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# При поступлении заявки в группу
@dp.chat_join_request_handler()
async def handle_join_request(join_request: types.ChatJoinRequest):
    data = load_data()
    user = join_request.from_user
    data['requests'].append({
        'user_id': user.id,
        'username': f"@{user.username}" if user.username else f"id:{user.id}",
        'chat_id': join_request.chat.id,
    })
    save_data(data)

# /joinlist (доступна всем)
@dp.message_handler(Command('joinlist'))
async def join_list(message: types.Message):
    data = load_data()
    if not data['requests']:
        await message.reply("📭 Нет входящих заявок.")
        return

    for req in data['requests']:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                text=f"✅ Принять {req['username']}",
                callback_data=f"approve:{req['user_id']}:{req['chat_id']}"
            )
        )
        await message.reply(f"📩 Заявка от {req['username']}", reply_markup=keyboard)

# Обработка кнопки "Принять"
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("approve:"))
async def process_approve(callback_query: types.CallbackQuery):
    _, user_id, chat_id = callback_query.data.split(':')
    user_id = int(user_id)
    chat_id = int(chat_id)
    admin_username = f"@{callback_query.from_user.username}" if callback_query.from_user.username else f"id:{callback_query.from_user.id}"

    data = load_data()
    data['requests'] = [r for r in data['requests'] if r['user_id'] != user_id]
    data['log'].append({
        'admin': admin_username,
        'user': f"id:{user_id}",
        'time': datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_data(data)

    await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
    await callback_query.message.edit_text(f"{admin_username} принял id:{user_id} ✅")

# /info4leader (только тебе)
@dp.message_handler(Command('info4leader'))
async def info_leader(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    if not data['log']:
        await message.reply("Журнал пуст.")
        return

    lines = [f"{entry['admin']} принял {entry['user']} — {entry['time']}" for entry in data['log']]
    await message.reply("\n".join(lines))

# /ping для UptimeRobot
@dp.message_handler(Command("ping"))
async def ping(message: types.Message):
    await message.answer("✅ Бот работает.")

# Web-сервер для Render (например, для /ping)
async def handle_web_ping(request):
    return web.Response(text="✅ Bot is alive!")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/ping', handle_web_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

async def on_startup(_):
    asyncio.create_task(start_webserver())

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
