"""Admin panel: Premium olish uchun majburiy obuna kanallarini boshqarish."""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import admin_channel_kb, cancel_kb
from loader import is_admin
from states import AdminChannelState

router = Router()


@router.message(F.text == "🗂 Majburiy kanallar")
async def channels_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🗂 Premium olish uchun majburiy kanallarni shu yerdan boshqarasiz.\n\n"
        "⚠️ Diqqat: kanal qo'shishdan oldin botni o'sha kanalga ADMIN qilib qo'shing, "
        "aks holda bot foydalanuvchilarning a'zoligini tekshira olmaydi.",
        reply_markup=admin_channel_kb
    )


@router.message(F.text == "➕ Kanal qo'shish")
async def add_channel_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "➕ Kanalni qo'shish uchun:\n\n"
        "1️⃣ O'sha kanaldan istalgan bitta postni shu yerga FORWARD (uzatib) yuboring\n"
        "yoki\n"
        "2️⃣ Kanal usernamesini yuboring (masalan: @mening_kanalim)\n\n"
        "❗️ Bot o'sha kanalda ADMIN bo'lishi shart.",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminChannelState.waiting_add_channel)


@router.message(AdminChannelState.waiting_add_channel)
async def add_channel_receive(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        if message.forward_from_chat:
            chat = message.forward_from_chat
        elif message.text:
            chat = await message.bot.get_chat(message.text.strip())
        else:
            await message.answer("❌ Kanal postini forward qiling yoki username yuboring.")
            return

        if chat.type not in ("channel", "supergroup"):
            await message.answer("❌ Bu kanal yoki guruh emas. Qayta urinib ko'ring.")
            return

        # Bot shu kanalda a'zoligini tekshirish
        try:
            await message.bot.get_chat_member(chat.id, message.bot.id)
        except Exception:
            await message.answer(
                "❌ Bot bu kanalda topilmadi.\n\n"
                "Iltimos, botni avval o'sha kanalga ADMIN sifatida qo'shing, so'ng qayta urinib ko'ring."
            )
            return

        await db.add_required_channel(chat.id, chat.username, chat.title)

        await message.answer(
            f"✅ Kanal qo'shildi: {chat.title}",
            reply_markup=admin_channel_kb
        )
        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}\n\nQayta urinib ko'ring yoki '❌ Bekor qilish' bosing.")


@router.message(F.text == "📋 Kanallar ro'yxati")
async def list_channels(message: Message):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_all_required_channels()
    if not channels:
        await message.answer("❌ Hozircha majburiy kanal qo'shilmagan.", reply_markup=admin_channel_kb)
        return

    text = "📋 Majburiy kanallar ro'yxati:\n\n"
    for idx, ch in enumerate(channels, 1):
        username = f"@{ch['channel_username']}" if ch['channel_username'] else "— (username yo'q)"
        text += f"{idx}. {ch['title']} ({username})\n"

    await message.answer(text, reply_markup=admin_channel_kb)


@router.message(F.text == "➖ Kanal o'chirish")
async def remove_channel_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_all_required_channels()
    if not channels:
        await message.answer("❌ Hozircha majburiy kanal qo'shilmagan.", reply_markup=admin_channel_kb)
        return

    text = "➖ O'chirmoqchi bo'lgan kanal raqamini yuboring:\n\n"
    for idx, ch in enumerate(channels, 1):
        text += f"{idx}. {ch['title']}\n"

    await state.update_data(channels=channels)
    await message.answer(text, reply_markup=cancel_kb)
    await state.set_state(AdminChannelState.waiting_remove_channel)


@router.message(AdminChannelState.waiting_remove_channel)
async def remove_channel_receive(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        data = await state.get_data()
        channels = data.get('channels', [])
        num = int(message.text.strip())

        if not (1 <= num <= len(channels)):
            await message.answer("❌ Noto'g'ri raqam. Qayta kiriting:")
            return

        chosen = channels[num - 1]
        await db.remove_required_channel(chosen['channel_id'])

        await message.answer(f"✅ Kanal o'chirildi: {chosen['title']}", reply_markup=admin_channel_kb)
        await state.clear()

    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
