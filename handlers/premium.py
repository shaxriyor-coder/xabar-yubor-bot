"""
Premium olish - majburiy obuna orqali, avtomatik.

Foydalanuvchi admin belgilagan kanallarga a'zo bo'ladi, "A'zo bo'ldim"
tugmasini bosadi - bot tekshiradi va hammasiga a'zo bo'lsa, admin
ishtirokisiz Premiumni avtomatik beradi.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_USERNAME
from database import db
from keyboards import main_kb, premium_kb

router = Router()


@router.message(F.text == "🎁 Premium olish")
async def buy_premium(message: Message):
    user_id = message.from_user.id

    channels = await db.get_all_required_channels()

    # Admin hali majburiy kanal qo'shmagan bo'lsa - to'siqsiz, darhol Premium beramiz
    if not channels:
        already_premium = await db.is_premium_active(user_id)
        await db.add_premium_user(user_id, days=30)

        if already_premium:
            await message.answer("✅ Premium muddatingiz 30 kunga uzaytirildi!", reply_markup=premium_kb)
        else:
            await message.answer(
                "🎉 Premium 30 kunga faollashtirildi!\n\n"
                "Endi '📤 Xabar yuborish' tugmasidan foydalanishingiz mumkin.",
                reply_markup=premium_kb
            )
        return

    buttons = []
    for ch in channels:
        if ch['channel_username']:
            buttons.append([InlineKeyboardButton(
                text=f"📢 {ch['title']}",
                url=f"https://t.me/{ch['channel_username']}"
            )])
    buttons.append([InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshirish", callback_data="check_subscription")])

    await message.answer(
        "🎁 Premium olish bepul!\n\n"
        "Quyidagi kanal(lar)ga a'zo bo'ling, so'ng pastdagi \"✅ A'zo bo'ldim\" tugmasini bosing - "
        "Premium avtomatik faollashadi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_cb(call: CallbackQuery):
    user_id = call.from_user.id
    channels = await db.get_all_required_channels()

    if not channels:
        await call.answer("⚠️ Kanallar sozlanmagan.", show_alert=True)
        return

    not_joined = []
    for ch in channels:
        try:
            member = await call.bot.get_chat_member(ch['channel_id'], user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch['title'])
        except Exception:
            not_joined.append(ch['title'])

    if not_joined:
        text = "❌ Siz hali quyidagi kanal(lar)ga a'zo emassiz:\n\n" + "\n".join(f"• {t}" for t in not_joined)
        await call.answer(text, show_alert=True)
        return

    already_premium = await db.is_premium_active(user_id)
    await db.add_premium_user(user_id, days=30)
    await call.answer("🎉 Tabriklaymiz! Premium faollashdi.", show_alert=True)

    if already_premium:
        await call.message.answer("✅ Premium muddatingiz 30 kunga uzaytirildi!", reply_markup=premium_kb)
    else:
        await call.message.answer(
            "🎉 Barcha kanallarga a'zo ekansiz - Premium 30 kunga faollashtirildi!\n\n"
            "Endi '📤 Xabar yuborish' tugmasidan foydalanishingiz mumkin.",
            reply_markup=premium_kb
        )


@router.message(F.text == "📞 Admin bilan bog'lanish")
async def contact_admin(message: Message):
    await message.answer(
        f"📞 Admin bilan bog'lanish uchun: [@{ADMIN_USERNAME}](https://t.me/{ADMIN_USERNAME})",
        parse_mode="Markdown",
        reply_markup=main_kb
    )


@router.message(F.text == "📝 Premium haqida")
async def premium_info(message: Message):
    import time

    user_id = message.from_user.id
    if await db.is_premium_active(user_id):
        expiry = await db.get_premium_expiry(user_id)
        remaining_days = int((expiry - time.time()) / (24 * 3600))

        session = await db.get_user_session(user_id)
        session_status = "✅ Ulangan" if session and session['is_active'] else "❌ Ulanmagan"

        await message.answer(
            "🎉 Siz Premium foydalanuvchisiz!\n\n"
            f"⏳ Qolgan muddat: {remaining_days} kun\n"
            f"📱 Akkaunt: {session_status}\n\n"
            "Muddat tugasa, 🎁 Premium olish tugmasi orqali kanallarga qayta a'zo bo'lib, "
            "Premiumni bepul uzaytirishingiz mumkin.",
            reply_markup=premium_kb
        )
    else:
        await message.answer(
            "❌ Sizning Premiumingiz tugagan. Endi oddiy foydalanuvchisiz.\n\n"
            "🎁 Premium olish tugmasi orqali qayta bepul olishingiz mumkin.",
            reply_markup=main_kb
        )

# =====================================================================
# ESKI TO'LOV TIZIMI (karta raqami + chek) - VAQTINCHA O'CHIRILGAN
#
# Kerak bo'lsa qayta yoqish uchun: kommentlarni olib tashlang,
# config.py dan CARD_NUMBER, PREMIUM_PRICE larni import qiling va
# database/payments.py dagi metodlardan foydalaning (ular hali ham bor).
# =====================================================================
#
# from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
# from aiogram.fsm.context import FSMContext
# from states import AdminBroadcastState
# from loader import ADMIN_IDS
#
# @router.message(F.text == "💳 Premium olish")
# async def buy_premium_old(message: Message):
#     user_id = message.from_user.id
#
#     cooldown = await db.get_cooldown(user_id)
#     if cooldown:
#         import time
#         remaining = int(cooldown - time.time())
#         mins = remaining // 60
#         secs = remaining % 60
#         await message.answer(f"⏳ {mins} min {secs} sekdan so'ng qayta urinib ko'ring.")
#         return
#
#     pay_kb = ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="✅ To'lov qildim")],
#             [KeyboardButton(text="⬅️ Ortga")]
#         ],
#         resize_keyboard=True
#     )
#
#     await message.answer(
#         f"💳 Premium narxi: {PREMIUM_PRICE} so'm\n\n"
#         f"To'lov uchun karta raqami: \n\n`{CARD_NUMBER}`\n\n"
#         "To'lovni qilgach quyidagi tugmadan foydalaning 👇",
#         parse_mode="Markdown",
#         reply_markup=pay_kb
#     )
#
# @router.message(F.text == "✅ To'lov qildim")
# async def payment_done(message: Message):
#     user_id = message.from_user.id
#
#     cooldown = await db.get_cooldown(user_id)
#     if cooldown:
#         await message.answer("❌ 5 daqiqa kutib qayta urinib ko'ring.")
#         return
#
#     await db.add_pending_payment(user_id)
#
#     await message.answer(
#         "✅ Iltimos, to'lov chekining rasm/screenshotini yuboring (faqat 1 ta).",
#         reply_markup=ReplyKeyboardRemove()
#     )
#
# @router.message(F.photo)
# async def handle_payment_check(message: Message, state: FSMContext):
#     user_id = message.from_user.id
#
#     current_state = await state.get_state()
#     if current_state == AdminBroadcastState.waiting_broadcast_message:
#         return
#
#     if not await db.is_payment_pending(user_id):
#         return
#
#     rejected_count = await db.get_rejected_count(user_id)
#
#     for admin_id in ADMIN_IDS:
#         try:
#             await message.bot.send_photo(
#                 admin_id,
#                 message.photo[-1].file_id,
#                 caption=(
#                     f"📩 Yangi to'lov cheki!\n"
#                     f"👤 User ID: {user_id}\n"
#                     f"Urinishlar: {rejected_count + 1}\n\n"
#                     f"✅ Tasdiqlash: /approve_{user_id}\n"
#                     f"❌ Rad etish: /reject_{user_id}"
#                 )
#             )
#         except Exception as e:
#             print(f"⚠️ Admin {admin_id} ga yuborishda xatolik: {e}")
#
#     await message.answer("✅ Chek yuborildi. Admin tekshirgandan so'ng Premium faollashadi.")
#
# @router.message(F.text.startswith("/approve_"))
# async def approve_payment(message: Message):
#     from loader import is_admin
#     if not is_admin(message.from_user.id):
#         return
#
#     user_id = int(message.text.split("_")[1])
#
#     await db.add_premium_user(user_id, days=30)
#     await db.remove_pending_payment(user_id)
#     await db.reset_rejected_count(user_id)
#     await db.remove_cooldown(user_id)
#
#     await message.bot.send_message(
#         user_id,
#         "🎉 To'lov tasdiqlandi! Sizga 1 oylik Premium berildi.",
#         reply_markup=premium_kb
#     )
#     await message.answer(f"✅ User {user_id} Premium bo'ldi.")
#
# @router.message(F.text.startswith("/reject_"))
# async def reject_payment(message: Message):
#     from loader import is_admin
#     if not is_admin(message.from_user.id):
#         return
#
#     user_id = int(message.text.split("_")[1])
#
#     await db.increment_rejected_count(user_id)
#     rejected_count = await db.get_rejected_count(user_id)
#
#     if rejected_count == 1:
#         await message.bot.send_message(
#             user_id,
#             "❌ To'lov rad etildi. Iltimos, chekni aniqroq qilib yana 1 marta yuboring. (1 urinish qoldi)",
#         )
#         await message.answer(f"❌ User {user_id} - 1-marta rad etildi.")
#         return
#
#     if rejected_count >= 2:
#         await db.add_cooldown(user_id, seconds=300)
#         await db.remove_pending_payment(user_id)
#
#         await message.bot.send_message(
#             user_id,
#             f"❌ Chek 2 marta rad etildi.\n"
#             f"Iltimos, 5 daqiqa kutib qayta urinib ko'ring yoki [admin bilan bog'laning](https://t.me/{ADMIN_USERNAME}).",
#             parse_mode="Markdown",
#             reply_markup=main_kb
#         )
#         await message.answer(f"❌ User {user_id} 2-marta rad etildi. 5 daqiqa cooldown.")
#
# =====================================================================
