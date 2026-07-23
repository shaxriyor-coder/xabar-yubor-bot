"""
Botni ishga tushirish uchun yagona nuqta.

Butun mantiq boshqa fayllarga bo'lingan:
- loader.py     -> bot, dp va umumiy runtime holatlar
- states.py     -> FSM holatlari
- keyboards.py  -> klaviaturalar
- database/     -> PostgreSQL bilan ishlash
- handlers/     -> barcha buyruq/tugma javoblari
- user_login.py -> foydalanuvchi akkauntiga ulanib xabar yuboradigan "userbot" logikasi
"""

import asyncio
import sys

# Windows konsoli ba'zan eski kodlashda (cp1252) ishlaydi va emoji belgilarni
# chop eta olmay xato beradi. Shu sabab chiqishni UTF-8'ga majburlaymiz.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from database import db
from handlers import router as handlers_router
from loader import bot, cleanup_handler, dp, userbot_handlers

dp.include_router(handlers_router)


async def main():
    await db.connect()
    print("✅ Database ulandi")

    print("🚀 Bot ishga tushdi!")
    try:
        await dp.start_polling(bot)
    finally:
        # Barcha ulangan akkauntlar (userbot handlerlar) ni tozalash
        for user_id in list(userbot_handlers.keys()):
            await cleanup_handler(user_id)
        print("✅ Barcha sessionlar yopildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Bot to'xtatildi")
