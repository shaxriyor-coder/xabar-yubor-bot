"""Admin panel: barcha yoki Premium userlarga ommaviy xabar yuborish."""

import asyncio

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import admin_kb, broadcast_confirm_kb, cancel_kb
from loader import is_admin
from states import AdminBroadcastState

router = Router()

BROADCAST_HINT = (
    "📝 Yubormoqchi bo'lgan xabaringizni yuboring:\n\n"
    "✅ Quyidagilarni yuborishingiz mumkin:\n"
    "• Matn xabar\n"
    "• Rasm (caption bilan)\n"
    "• Video (caption bilan)\n"
    "• Fayl/document (caption bilan)"
)


@router.message(F.text == "📢 Barcha userlarga xabar yuborish")
async def broadcast_all_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(broadcast_type="all")
    await message.answer(
        "📢 Barcha userlarga xabar yuborish\n\n" + BROADCAST_HINT,
        reply_markup=cancel_kb
    )
    await state.set_state(AdminBroadcastState.waiting_broadcast_message)


@router.message(F.text == "💎 Premium userlarga xabar")
async def broadcast_premium_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(broadcast_type="premium")
    await message.answer(
        "💎 Premium userlarga xabar yuborish\n\n" + BROADCAST_HINT,
        reply_markup=cancel_kb
    )
    await state.set_state(AdminBroadcastState.waiting_broadcast_message)


@router.message(AdminBroadcastState.waiting_broadcast_message)
async def receive_broadcast_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    broadcast_type = data.get('broadcast_type', 'all')

    message_type = "text"
    message_content = None
    caption = None
    file_id = None

    if message.photo:
        message_type = "photo"
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
    elif message.video:
        message_type = "video"
        file_id = message.video.file_id
        caption = message.caption or ""
    elif message.document:
        message_type = "document"
        file_id = message.document.file_id
        caption = message.caption or ""
    elif message.text:
        message_type = "text"
        message_content = message.text
    else:
        await message.answer(
            "❌ Bu turdagi xabar qo'llab-quvvatlanmaydi!\n\n"
            "✅ Quyidagilarni yuborishingiz mumkin:\n"
            "- Matn\n"
            "- Rasm\n"
            "- Video\n"
            "- Fayl (document)",
            reply_markup=admin_kb
        )
        await state.clear()
        return

    if broadcast_type == "premium":
        users = await db.get_all_premium_users()
        user_ids = [u['user_id'] for u in users]
        target_text = f"{len(user_ids)} ta Premium user"
    else:
        users = await db.get_all_users()
        user_ids = [u['user_id'] for u in users]
        target_text = f"{len(user_ids)} ta user"

    if not user_ids:
        await message.answer("❌ Userlar topilmadi!", reply_markup=admin_kb)
        await state.clear()
        return

    content_preview = message_content[:50] if message_content else f"[{message_type.upper()}]"

    await message.answer(
        f"📊 Xabar yuborish tayyorlandi!\n\n"
        f"👥 Qabul qiluvchilar: {target_text}\n"
        f"📝 Turi: {message_type.upper()}\n"
        f"💬 Kontent: {content_preview}...\n\n"
        "⚠️ Yuborishni tasdiqlaysizmi?",
        reply_markup=broadcast_confirm_kb
    )

    await state.update_data(
        user_ids=user_ids,
        message_type=message_type,
        message_content=message_content,
        caption=caption,
        file_id=file_id
    )


@router.message(F.text == "✅ Yuborish", StateFilter(AdminBroadcastState.waiting_broadcast_message))
async def confirm_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_ids = data.get('user_ids', [])
    message_type = data.get('message_type', 'text')
    message_content = data.get('message_content')
    caption = data.get('caption')
    file_id = data.get('file_id')

    await message.answer("⏳ Xabar yuborish boshlandi...", reply_markup=admin_kb)

    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            if message_type == "photo":
                await message.bot.send_photo(user_id, file_id, caption=caption)
            elif message_type == "video":
                await message.bot.send_video(user_id, file_id, caption=caption)
            elif message_type == "document":
                await message.bot.send_document(user_id, file_id, caption=caption)
            else:  # text
                await message.bot.send_message(user_id, message_content)

            sent_count += 1

            # Har 10 userdan keyin kichik kutish
            if sent_count % 10 == 0:
                await asyncio.sleep(0.5)

        except (TelegramForbiddenError, TelegramBadRequest):
            # User botni bloklagan yoki user topilmadi
            failed_count += 1
        except Exception as e:
            print(f"⚠️ User {user_id} ga yuborishda xatolik: {e}")
            failed_count += 1

    await message.answer(
        f"✅ Xabar yuborish tugadi!\n\n"
        f"📤 Yuborildi: {sent_count}\n"
        f"❌ Muvaffaqiyatsiz: {failed_count}\n"
        f"📊 Jami: {len(user_ids)}",
        reply_markup=admin_kb
    )

    await state.clear()

# "❌ Bekor qilish" ushbu bosqichda ham bosilishi mumkin - u handlers/common.py
# dagi umumiy cancel_action orqali avtomatik ushlanadi, alohida handler shart emas.
