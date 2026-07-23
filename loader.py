"""
Bot va dispatcher shu yerda yaratiladi, hamma joydan shu yerdan import qilinadi.

Bu fayl "markaz" hisoblanadi: barcha handler fayllar shu yerdagi `bot`, `dp`,
`is_admin`, `get_or_create_handler` kabi umumiy narsalarni import qiladi.
Aylanma import (circular import) bo'lmasligi uchun bu fayl handlerlarni
o'zi import qilmaydi - ularni bog'lash ishi bot.py da bo'ladi.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from database import db
from keyboards import admin_kb, premium_kb, main_kb
from user_login import UserBotHandler

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# 2 TA ADMIN - config.py ga ADMIN_ID2 qo'shsangiz, shu yerga qo'shing:
# ADMIN_IDS = [ADMIN_ID, ADMIN_ID2]
ADMIN_IDS = [ADMIN_ID]

# Har bir user uchun alohida ishlaydigan runtime holatlar (RAM'da saqlanadi)
userbot_handlers = {}  # {user_id: UserBotHandler}
user_tasks = {}         # {user_id: asyncio.Task} - kampaniya (xabar yuborish) tasklari
qr_tasks = {}            # {user_id: asyncio.Task} - QR login kutish jarayoni


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi adminligini tekshirish"""
    return user_id in ADMIN_IDS


def get_or_create_handler(user_id: int) -> UserBotHandler:
    """Har bir user uchun alohida UserBotHandler yaratadi (yoki mavjudini qaytaradi)"""
    if user_id not in userbot_handlers:
        userbot_handlers[user_id] = UserBotHandler(bot_instance=bot, user_id=user_id)
    return userbot_handlers[user_id]


def cancel_qr_task(user_id: int):
    """User uchun kutilayotgan QR login jarayonini bekor qilish"""
    if user_id in qr_tasks:
        qr_tasks[user_id].cancel()
        del qr_tasks[user_id]


async def cleanup_handler(user_id: int):
    """User handlerini va unga bog'liq barcha jarayonlarni tozalash"""
    cancel_qr_task(user_id)
    if user_id in userbot_handlers:
        handler = userbot_handlers[user_id]
        await handler.stop()
        del userbot_handlers[user_id]


async def get_user_menu(user_id: int):
    """User turiga mos asosiy menyu klaviaturasini qaytarish"""
    if is_admin(user_id):
        return admin_kb
    if await db.is_premium_active(user_id):
        return premium_kb
    return main_kb
