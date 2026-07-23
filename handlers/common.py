"""Umumiy buyruqlar: /start, "Bu bot haqida", "Men haqimda", "Ortga"/"Bekor qilish"."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import admin_kb, premium_kb, main_kb
from loader import cancel_qr_task, get_user_menu, is_admin

router = Router()


@router.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id

    # Userni ro'yxatga olish (agar yangi bo'lsa)
    await db.register_user(user_id)

    # Admin uchun alohida panel
    if is_admin(user_id):
        await message.answer(
            "👨‍💼 Admin panelga xush kelibsiz!",
            reply_markup=admin_kb
        )
        return

    if await db.is_premium_active(user_id):
        await message.answer(
            "🎉 Sizda Premium mavjud! Foydalanishingiz mumkin ✅",
            reply_markup=premium_kb
        )
    else:
        await message.answer(
            "👋 Salom! Quyidagi menyudan foydalaning 👇",
            reply_markup=main_kb
        )


@router.message(F.text == "📝 Bu bot haqida")
async def about_bot(message: Message):
    menu_kb = await get_user_menu(message.from_user.id)
    await message.answer(
        "📌 Bu bot sizning o'rningizdan guruhlaringizga xabar/reklamani "
        "avtomatik va doimiy ravishda yuborib turadi.\n\n"
        "📖 Foydalanish tartibi:\n\n"
        "1️⃣ '🎁 Premium olish' tugmasini bosing va ko'rsatilgan kanal(lar)ga "
        "a'zo bo'ling - bu butunlay bepul\n\n"
        "2️⃣ Telegram'da 'Xabar' nomli jild (folder) yarating va reklama "
        "yubormoqchi bo'lgan GURUHLARINGIZNI o'sha jildga qo'shing "
        "(kanallarni qo'shmang)\n\n"
        "3️⃣ '📤 Xabar yuborish' tugmasini bosing va Telegram akkauntingizni "
        "ulang (QR kod skanerlab yoki telefon raqam orqali)\n\n"
        "4️⃣ Bot 'Xabar' jildidagi guruhlarni o'zi topadi\n\n"
        "5️⃣ Necha soniyada bir marta yuborilishini kiriting (kamida 17 soniya)\n\n"
        "6️⃣ Yubormoqchi bo'lgan xabaringizni (matn, rasm, video yoki fayl) yuboring\n\n"
        "✅ Tayyor! Endi bot shu xabarni tanlangan guruhlarga o'zi, "
        "takrorlab yuborib turadi. To'xtatmoqchi bo'lsangiz - "
        "'🔄 Kampaniyani to'xtatish' tugmasini bosasiz.\n\n"
        "🔐 Akkauntingiz xavfsiz: faqat shu xabarni yuborish uchun ishlatiladi, "
        "boshqa hech narsaga tegilmaydi.\n\n"
        "⚠️ Akkauntingiz bloklanmasligi uchun:\n"
        "• 'Xabar' jildiga faqat o'zingiz haqiqiy a'zo bo'lgan guruhlarni qo'shing\n"
        "• Bitta xabarni juda ko'p (o'nlab/yuzlab) turli guruhga yubormang\n"
        "• Intervalni kichik qilib qo'ymang - qancha katta bo'lsa, shuncha xavfsiz\n"
        "• Xabar matnida shubhali/taqiqlangan havolalar bo'lmasin\n\n"
        "👤 Muallif: [@Shaxriyor_Egamberdiyev](https://t.me/Shaxriyor_Egamberdiyev)\n"
        "👥 Jamoa: LeadersSoft team",
        parse_mode="Markdown",
        reply_markup=menu_kb
    )


@router.message(F.text == "ℹ️ Men haqimda")
async def about_me(message: Message):
    import time
    from datetime import datetime

    user_id = message.from_user.id
    menu_kb = await get_user_menu(user_id)

    full_name = message.from_user.full_name or "Noma'lum"
    username = f"@{message.from_user.username}" if message.from_user.username else "—"

    user_info = await db.get_user_info(user_id)
    created_at = user_info.get('created_at', 0) if user_info else 0
    joined_date = datetime.fromtimestamp(created_at).strftime('%d.%m.%Y') if created_at else "Noma'lum"

    is_premium = await db.is_premium_active(user_id)
    if is_premium:
        expiry = await db.get_premium_expiry(user_id)
        remaining_days = int((expiry - time.time()) / (24 * 3600))
        premium_status = f"✅ Faol ({remaining_days} kun qoldi)"
    else:
        premium_status = "❌ Faol emas"

    session = await db.get_user_session(user_id)
    account_status = "✅ Ulangan" if session and session.get('is_active') else "❌ Ulanmagan"

    await message.answer(
        f"👤 Ism: {full_name}\n"
        f"🔖 Username: {username}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📅 Botga qo'shilgan sana: {joined_date}\n\n"
        f"💎 Premium: {premium_status}\n"
        f"📱 Telegram akkaunt: {account_status}",
        parse_mode="Markdown",
        reply_markup=menu_kb
    )


async def _return_to_menu(message: Message, state: FSMContext, text: str):
    """Joriy jarayonni to'xtatib, foydalanuvchini o'z menyusiga qaytarish"""
    user_id = message.from_user.id

    await state.clear()
    cancel_qr_task(user_id)  # agar QR login kutilayotgan bo'lsa, uni ham bekor qilish

    menu_kb = await get_user_menu(user_id)
    await message.answer(text, reply_markup=menu_kb)


@router.message(F.text == "⬅️ Ortga")
async def back_to_menu(message: Message, state: FSMContext):
    await _return_to_menu(message, state, "🏠 Bosh menyu")


@router.message(F.text == "❌ Bekor qilish")
async def cancel_action(message: Message, state: FSMContext):
    """
    Har qanday ko'p bosqichli jarayonni (login, guruh tanlash, interval,
    admin kanal/broadcast) istalgan vaqtda bekor qilish uchun universal tugma.
    """
    await _return_to_menu(message, state, "❌ Bekor qilindi.")
