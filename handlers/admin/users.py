"""Admin panel: Premium userlar ro'yxati/qidiruv, statistika, Premium olib qo'yish."""

import time
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import admin_kb, cancel_kb, main_kb
from loader import cleanup_handler, is_admin, user_tasks, userbot_handlers
from states import AdminSearchState

router = Router()


@router.message(F.text == "👥 Premium userlar ro'yxati")
async def premium_users_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await db.get_all_premium_users()

    if not users:
        await message.answer("❌ Premium userlar yo'q", reply_markup=admin_kb)
        return

    text = "<b>👥 Premium userlar ro'yxati:</b>\n\n"

    for idx, user in enumerate(users[:20], 1):  # Faqat 20 ta ko'rsatish
        user_id = user['user_id']
        premium_expiry = user['premium_expiry']
        created_at = user.get('created_at', 0)

        try:
            chat = await message.bot.get_chat(user_id)

            full_name = chat.full_name if chat.full_name else "Noma'lum"
            full_name = full_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            username = f"@{chat.username}" if chat.username else "—"

        except Exception as e:
            print(f"⚠️ User {user_id} ma'lumotini ololmadim: {e}")
            full_name = "Noma'lum"
            username = "—"

        if created_at:
            start_date = datetime.fromtimestamp(created_at).strftime('%d.%m.%Y')
        else:
            start_date = "Noma'lum"

        expiry_date = datetime.fromtimestamp(premium_expiry).strftime('%d.%m.%Y %H:%M')
        remaining = int((premium_expiry - time.time()) / (24 * 3600))

        text += f"{idx}. 👤 <b>{full_name}</b>\n"
        text += f"   🆔 ID: <code>{user_id}</code>\n"
        text += f"   📱 Username: {username}\n"
        text += f"   📅 Boshlangan: {start_date}\n"
        text += f"   ⏳ Tugashi: {expiry_date}\n"
        text += f"   📊 Qolgan: {remaining} kun\n"
        text += f"   🗑 O'chirish: /removepremium{user_id}\n\n"

    if len(users) > 20:
        text += f"\n... va yana {len(users) - 20} ta user"

    await message.answer(text, parse_mode="HTML", reply_markup=admin_kb)


@router.message(F.text == "🔍 User qidirish")
async def search_user_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔍 User ID ni kiriting:\n\n"
        "Masalan: 123456789",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminSearchState.waiting_user_id)


@router.message(AdminSearchState.waiting_user_id)
async def search_user_result(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        search_user_id = int(message.text.strip())

        is_premium = await db.is_premium_active(search_user_id)

        if not is_premium:
            await message.answer(
                f"❌ User {search_user_id} Premium emas yoki topilmadi",
                reply_markup=admin_kb
            )
            await state.clear()
            return

        expiry = await db.get_premium_expiry(search_user_id)
        user_info = await db.get_user_info(search_user_id)

        try:
            chat = await message.bot.get_chat(search_user_id)
            full_name = chat.full_name if chat.full_name else "Noma'lum"
            username = f"@{chat.username}" if chat.username else "—"
        except Exception:
            full_name = "Noma'lum"
            username = "—"

        created_at = user_info.get('created_at', 0) if user_info else 0
        if created_at:
            start_date = datetime.fromtimestamp(created_at).strftime('%d.%m.%Y %H:%M')
        else:
            start_date = "Noma'lum"

        expiry_date = datetime.fromtimestamp(expiry).strftime('%d.%m.%Y %H:%M')
        remaining = int((expiry - time.time()) / (24 * 3600))

        session = await db.get_user_session(search_user_id)
        session_status = "✅ Ulangan" if session and session['is_active'] else "❌ Ulanmagan"

        text = "👤 User ma'lumotlari:\n\n"
        text += f"👤 Ism: {full_name}\n"
        text += f"🆔 User ID: `{search_user_id}`\n"
        text += f"📱 Username: {username}\n"
        text += f"📅 Premium boshlangan: {start_date}\n"
        text += f"⏳ Premium tugashi: {expiry_date}\n"
        text += f"📊 Qolgan muddat: {remaining} kun\n"
        text += f"📱 Session: {session_status}\n\n"
        text += f"🗑 Premium o'chirish: /removepremium{search_user_id}"

        await message.answer(text, parse_mode="Markdown", reply_markup=admin_kb)
        await state.clear()

    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam kiriting!", reply_markup=admin_kb)
        await state.clear()


@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    stats = await db.get_bot_statistics()

    text = "📊 Bot statistikasi:\n\n"
    text += f"👥 Jami userlar: {stats['total_users']}\n"
    text += f"💎 Premium userlar: {stats['premium_users']}\n"
    text += f"📤 Faol kampaniyalar: {stats['active_campaigns']}\n"
    text += f"✅ Yuborilgan xabarlar: {stats['total_sent']}\n"
    text += f"❌ Muvaffaqiyatsiz: {stats['total_failed']}\n"

    await message.answer(text, reply_markup=admin_kb)


@router.message(lambda msg: msg.text and (msg.text.startswith('/removepremium') or msg.text.startswith('/remove_premium_')))
async def remove_premium(message: Message):
    if not is_admin(message.from_user.id):
        return

    try:
        text = message.text.strip()

        if text.startswith('/removepremium'):
            user_id = int(text.replace('/removepremium', ''))
        elif text.startswith('/remove_premium_'):
            user_id = int(text.replace('/remove_premium_', ''))
        else:
            return

        is_premium = await db.is_premium_active(user_id)

        if not is_premium:
            await message.answer(f"❌ User {user_id} Premium emas", reply_markup=admin_kb)
            return

        await db.remove_premium(user_id)
        print(f"📊 User {user_id}: premium_expiry = 0 qilindi")

        if user_id in user_tasks:
            try:
                user_tasks[user_id].cancel()
                del user_tasks[user_id]
                print(f"⏹ User {user_id} ning kampaniyasi to'xtatildi")
            except Exception as e:
                print(f"⚠️ Kampaniyani to'xtatishda xatolik: {e}")

        await db.stop_user_campaigns(user_id)

        if user_id in userbot_handlers:
            try:
                await cleanup_handler(user_id)
                print(f"🧹 User {user_id} handler tozalandi")
            except Exception as e:
                print(f"⚠️ Handler tozalashda xatolik: {e}")

        try:
            await message.bot.send_message(
                user_id,
                "❌ *Sizning Premium obunangiz bekor qilindi!*\n\n"
                "📌 Endi siz oddiy foydalanuvchisiz.\n"
                "🎁 Qayta Premium olish uchun '🎁 Premium olish' tugmasini bosing.\n\n"
                "❓ Agar bu xato bo'lsa, admin bilan bog'laning.",
                parse_mode="Markdown",
                reply_markup=main_kb
            )
            print(f"✅ User {user_id} ga xabar yuborildi va HOME sahifaga o'tkazildi")
        except Exception as e:
            print(f"⚠️ User {user_id} ga xabar yuborishda xatolik: {e}")

        await message.answer(
            f"✅ *Premium muvaffaqiyatli olib qo'yildi!*\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"📊 Holat: Oddiy user\n"
            f"📱 Session: Saqlanib qoldi\n"
            f"📩 Userga xabar: Yuborildi ✅",
            parse_mode="Markdown",
            reply_markup=admin_kb
        )

    except ValueError:
        await message.answer("❌ Noto'g'ri format! To'g'ri format: /remove_premium_123456789", reply_markup=admin_kb)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", reply_markup=admin_kb)
