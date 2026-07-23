"""
Telegram akkauntga kirish: QR kod yoki telefon raqam + kod, kerak bo'lsa 2FA parol.

Bu login usuli "📤 Xabar yuborish" bosilganda (handlers/messaging.py) ishga
tushadi - bu yerda faqat kirish jarayonining o'zi bor.
"""

import asyncio

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import db
from keyboards import cancel_kb, premium_kb
from loader import cancel_qr_task, get_or_create_handler, qr_tasks
from states import PhoneState
from utils import INTERNET_REMINDER, make_qr_image

router = Router()


@router.callback_query(F.data == "login_phone")
async def login_phone_cb(call: CallbackQuery, state: FSMContext):
    cancel_qr_task(call.from_user.id)
    await call.message.answer(
        "📱 Iltimos, telefon raqamingizni kiriting (masalan: +998901234567):" + INTERNET_REMINDER,
        reply_markup=cancel_kb
    )
    await state.set_state(PhoneState.waiting_phone)
    await call.answer()


@router.callback_query(F.data == "login_qr")
async def login_qr_cb(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await call.answer()
    cancel_qr_task(user_id)

    handler = get_or_create_handler(user_id)
    try:
        url = await handler.start_qr_login(user_id)
    except Exception as e:
        await call.message.answer(f"❌ QR kod yaratishda xatolik: {str(e)}")
        return

    qr_image = make_qr_image(url)
    await call.bot.send_photo(
        user_id,
        qr_image,
        caption=(
            "📷 Ushbu QR kodni telefoningizdagi Telegram ilovasi orqali skaner qiling:\n\n"
            "Sozlamalar → Qurilmalar → QR kodni skaner qilish\n\n"
            "⏳ Kod 60 soniya amal qiladi." + INTERNET_REMINDER
        )
    )

    task = asyncio.create_task(wait_for_qr_login(call.bot, user_id, state))
    qr_tasks[user_id] = task


async def wait_for_qr_login(bot, user_id: int, state: FSMContext):
    """QR kod skaner qilinishini kutish va natijani foydalanuvchiga bildirish"""
    handler = get_or_create_handler(user_id)
    try:
        session_string = await handler.wait_qr_login(user_id)
        phone = await handler.get_logged_in_phone()
        await db.save_user_session(user_id, phone, session_string)
        handler.begin_watching_session(user_id)

        await bot.send_message(
            user_id,
            "✅ Muvaffaqiyatli login qilindi!\n\n"
            "Endi xabar yuborish uchun qayta '📤 Xabar yuborish' tugmasini bosing." + INTERNET_REMINDER,
            reply_markup=premium_kb
        )

    except Exception as e:
        error_msg = str(e)

        if "2FA_REQUIRED" in error_msg:
            await state.set_state(PhoneState.waiting_2fa_password)
            await bot.send_message(
                user_id,
                "🔐 Sizning akkauntingizda 2-bosqichli parol yoqilgan!\n\n"
                "Iltimos, 2FA parolingizni kiriting:" + INTERNET_REMINDER,
                reply_markup=cancel_kb
            )
        elif "QR_TIMEOUT" in error_msg:
            await bot.send_message(
                user_id,
                "⌛ QR kodning amal qilish muddati tugadi.\n\n"
                "Qayta urinish uchun '📤 Xabar yuborish' tugmasini bosing.",
                reply_markup=premium_kb
            )
        else:
            await bot.send_message(user_id, f"❌ Xatolik: {error_msg}", reply_markup=premium_kb)

    finally:
        qr_tasks.pop(user_id, None)


@router.message(PhoneState.waiting_phone)
async def receive_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    user_id = message.from_user.id

    if not phone.startswith('+'):
        await message.answer("❌ Telefon raqam '+' belgisi bilan boshlanishi kerak!")
        return

    try:
        handler = get_or_create_handler(user_id)
        await handler.send_code(user_id, phone)

        await state.update_data(phone=phone)
        await state.set_state(PhoneState.waiting_code)

        await message.answer(
            "✅ Telegram'dan kod yuborildi!\n\n"
            "🔐 Kodni kiriting (masalan: 12345):" + INTERNET_REMINDER,
            reply_markup=cancel_kb
        )
    except Exception as e:
        await message.answer(
            f"❌ Xatolik: {str(e)}\n\n"
            "Qayta urinib ko'ring.",
            reply_markup=premium_kb
        )
        await state.clear()


@router.message(PhoneState.waiting_code)
async def receive_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone = data['phone']
    user_id = message.from_user.id

    try:
        handler = get_or_create_handler(user_id)
        session_string = await handler.sign_in(user_id, phone, code)

        await db.save_user_session(user_id, phone, session_string)
        handler.begin_watching_session(user_id)

        await message.answer(
            "✅ Muvaffaqiyatli login qilindi!\n\n"
            "Endi xabar yuborish uchun qayta '📤 Xabar yuborish' tugmasini bosing." + INTERNET_REMINDER,
            reply_markup=premium_kb
        )
        await state.clear()

    except Exception as e:
        error_msg = str(e)

        if "2FA_REQUIRED" in error_msg or "PASSWORD_HASH_INVALID" in error_msg:
            await state.set_state(PhoneState.waiting_2fa_password)
            await message.answer(
                "🔐 Sizning akkauntingizda 2-bosqichli parol yoqilgan!\n\n"
                "Iltimos, 2FA parolingizni kiriting:" + INTERNET_REMINDER,
                reply_markup=cancel_kb
            )
        else:
            await message.answer(
                f"❌ Kod noto'g'ri yoki xatolik: {error_msg}",
                reply_markup=premium_kb
            )
            await state.clear()


@router.message(PhoneState.waiting_2fa_password)
async def receive_2fa_password(message: Message, state: FSMContext):
    password = message.text.strip()
    user_id = message.from_user.id

    # Xavfsizlik uchun parolni o'chirish
    try:
        await message.delete()
    except Exception:
        pass

    try:
        handler = get_or_create_handler(user_id)
        session_string = await handler.sign_in_with_2fa(user_id, password)
        # Telefon raqami akkauntning o'zidan olinadi (kod yoki QR - ikkalasida ham ishlaydi)
        phone = await handler.get_logged_in_phone()

        await db.save_user_session(user_id, phone, session_string)
        handler.begin_watching_session(user_id)

        await message.bot.send_message(
            user_id,
            "✅ Muvaffaqiyatli login qilindi!\n\n"
            "Endi xabar yuborish uchun qayta '📤 Xabar yuborish' tugmasini bosing." + INTERNET_REMINDER,
            reply_markup=premium_kb
        )
        await state.clear()

    except Exception as e:
        await message.bot.send_message(
            user_id,
            f"❌ 2FA parol noto'g'ri yoki xatolik: {str(e)}",
            reply_markup=premium_kb
        )
        await state.clear()
