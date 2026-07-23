"""
Xabar yuborish (kampaniya): guruhlarni tanlash, interval, xabar matni,
kampaniyani boshlash/to'xtatish va akkauntdan chiqish.
"""

import asyncio

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import campaign_kb, cancel_kb, login_choice_kb, main_kb, premium_kb
from loader import cleanup_handler, get_or_create_handler, user_tasks
from states import IntervalState, MessageState
from utils import INTERNET_REMINDER

router = Router()

INTERVAL_HINT = (
    "⏰ Iltimos, har bir guruhga xabar yuborish orasidagi intervalni kiriting (sekundlarda):\n\n"
    "🔸 Minimum: 17 sekund\n"
    "🔸 Tavsiya: 20-30 sekund\n\n"
    "💡 Masalan: 20 (har 20 sekundda bitta guruhga xabar yuboriladi)\n"
    "📌 Agar minut kiritmoqchi bo'lsangiz, sekundga o'zgartiring:\n"
    "   1 minut = 60 sekund\n"
    "   2 minut = 120 sekund\n"
    "   5 minut = 300 sekund"
)

FOLDER_INSTRUCTIONS = (
    "❌ 'Xabar' nomli jild (folder) topilmadi.\n\n"
    "📁 Xabar yuborish uchun avval Telegram'da 'Xabar' nomli jild yaratib, "
    "reklama yubormoqchi bo'lgan GURUHLARINGIZNI o'sha jildga qo'shishingiz kerak:\n\n"
    "1️⃣ Telegram sozlamalari → Suhbat jildlari (Chat Folders)\n"
    "2️⃣ '+ Jild qo'shish' tugmasini bosing\n"
    "3️⃣ Jild nomini aynan 'Xabar' deb yozing\n"
    "4️⃣ Faqat reklama yubormoqchi bo'lgan GURUHLARNI qo'shing\n"
    "5️⃣ Saqlang va qayta '📤 Xabar yuborish' tugmasini bosing\n\n"
    "🚫 MUHIM: Jildga kanallarni qo'shmang - ban olishingiz mumkin!"
)


@router.message(F.text == "📤 Xabar yuborish")
async def start_messaging(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if not await db.is_premium_active(user_id):
        await message.answer("❌ Bu funksiya faqat Premium userlar uchun!", reply_markup=main_kb)
        return

    # Sessiya bormi tekshirish
    session = await db.get_user_session(user_id)

    if not session or not session['is_active']:
        # Login usulini tanlash - ishonch xabari bilan
        await message.answer(
            "🔐 Xabarlaringizni avtomatik yuborish uchun botga bir martalik "
            "shaxsiy Telegram akkauntingizga kirish kerak.\n\n"
            "✅ Bu bot ishonchli: akkaunt ma'lumotlaringiz faqat xabar yuborish uchun ishlatiladi "
            "va boshqa hech kimga berilmaydi.\n\n"
            "👇 Kirish usulini tanlang:" + INTERNET_REMINDER,
            reply_markup=login_choice_kb
        )
        return

    # Sessiya mavjud - guruhlarni olish
    try:
        handler = get_or_create_handler(user_id)

        # 1. "Xabar" jildini tekshirish
        folder_groups = await handler.get_groups_from_folder(user_id, session['session_string'], folder_name="Xabar")

        if folder_groups:
            # Agar jild topilsa, undagi guruhlarni avtomatik tanlash
            await state.update_data(selected_groups=folder_groups)

            await message.answer(
                f"✅ 'Xabar' jildi topildi!\n"
                f"📊 {len(folder_groups)} ta guruh tanlandi\n\n" + INTERVAL_HINT + INTERNET_REMINDER,
                reply_markup=cancel_kb
            )
            await state.set_state(IntervalState.waiting_interval)

        else:
            # "Xabar" jildi topilmasa - foydalanuvchining BARCHA guruhlarini
            # ko'rsatib, qo'lda tanlatish o'rniga aniq yo'riqnoma beramiz.
            #
            # Nega: agar minglab foydalanuvchi jildsiz shu tugmani bossa, bot
            # har birining barcha (hattoki yuzlab) guruhini Telegram'dan
            # birma-bir so'rashga majbur bo'lardi - bu serverni sekinlashtiradi
            # va Telegram flood-limitiga tutilish xavfini oshiradi. Bundan
            # tashqari, tasodifan shaxsiy/oilaviy guruhga reklama ketib qolishi
            # mumkin edi. "Xabar" jildi bu ikkala xavfni ham yo'q qiladi.
            await message.answer(FOLDER_INSTRUCTIONS, reply_markup=premium_kb)

    except Exception as e:
        error_text = str(e)
        if "SESSION_INVALID" in error_text:
            await db.delete_user_session(user_id)
            await cleanup_handler(user_id)
            await message.answer(
                "❌ Session yaroqsiz bo'lib qolgan.\n\n"
                "🔐 Qayta ulanish uchun kirish usulini tanlang:",
                reply_markup=login_choice_kb
            )
            return

        await message.answer(
            f"❌ Xatolik: {error_text}\n\n"
            "Iltimos, qayta urinib ko'ring. Agar session muammosi bo'lsa, qayta '📤 Xabar yuborish' ni bosib login qiling.",
            reply_markup=premium_kb
        )


@router.message(IntervalState.waiting_interval)
async def receive_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())

        if interval < 17:
            await message.answer(
                "❌ Interval kamida 17 sekund bo'lishi kerak!\n\n"
                "📌 Minut uchun:\n"
                "   1 minut = 60 sekund\n"
                "   2 minut = 120 sekund\n"
                "   5 minut = 300 sekund\n\n"
                "Qayta kiriting:"
            )
            return

        data = await state.get_data()
        selected_groups = data.get('selected_groups', [])

        if not selected_groups:
            await message.answer("❌ Guruhlar topilmadi. Qayta boshlang.", reply_markup=premium_kb)
            await state.clear()
            return

        await state.update_data(interval=interval)
        await state.set_state(MessageState.waiting_message)

        groups_text = f"📋 {len(selected_groups)} ta guruh tanlandi:\n\n"
        for idx, group in enumerate(selected_groups[:15], 1):
            groups_text += f"{idx}. {group['title']}\n"

        if len(selected_groups) > 15:
            groups_text += f"\n... va yana {len(selected_groups) - 15} ta guruh"

        groups_text += f"\n⏰ Interval: {interval} sekund"
        groups_text += "\n\n📝 Endi yubormoqchi bo'lgan xabaringizni yuboring:"
        groups_text += "\n\n✅ Quyidagilarni yuborishingiz mumkin:"
        groups_text += "\n• Matn xabar"
        groups_text += "\n• Rasm (caption bilan)"
        groups_text += "\n• Video (caption bilan)"
        groups_text += "\n• Fayl/document (caption bilan)"
        groups_text += INTERNET_REMINDER

        await message.answer(groups_text, reply_markup=cancel_kb)

    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting! Qayta kiriting:")


@router.message(MessageState.waiting_message)
async def receive_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    selected_groups = data.get('selected_groups', [])
    interval = data.get('interval', 5)

    if not selected_groups:
        await message.answer("❌ Guruhlar topilmadi. Qayta boshlang.", reply_markup=premium_kb)
        await state.clear()
        return

    # Xabar turini aniqlash
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
            reply_markup=premium_kb
        )
        return

    # Userbot'ga yuborish topshirish
    session = await db.get_user_session(user_id)
    if not session or not session.get('is_active') or not session.get('session_string'):
        await state.clear()
        await message.answer(
            "❌ Telegram akkauntingiz hali ulanmagan yoki session faol emas.\n\n"
            "Qayta ulanish uchun '📤 Xabar yuborish' tugmasini yana bosing.",
            reply_markup=premium_kb
        )
        return

    # Kampaniya yaratish
    group_ids = [g['id'] for g in selected_groups]
    campaign_id = await db.create_campaign(
        user_id,
        message_content or caption or "",
        group_ids,
        interval,
        message_type=message_type,
        file_id=file_id
    )

    handler = get_or_create_handler(user_id)

    task = asyncio.create_task(
        handler.start_campaign(user_id, campaign_id, session['session_string'], interval)
    )
    user_tasks[user_id] = task

    content_preview = message_content[:50] if message_content else f"[{message_type.upper()}]"

    await message.answer(
        f"✅ Xabar yuborish boshlandi!\n\n"
        f"📤 {len(selected_groups)} ta guruhga xabar yuborilmoqda\n"
        f"⏰ Interval: {interval} sekund\n"
        f"📝 Turi: {message_type.upper()}\n"
        f"💬 Kontent: {content_preview}...\n\n"
        "⏳ Progress haqida xabar beriladi..." + INTERNET_REMINDER,
        reply_markup=campaign_kb
    )
    await state.clear()


@router.message(F.text == "🔄 Kampaniyani to'xtatish")
async def stop_campaign(message: Message):
    user_id = message.from_user.id

    if not await db.is_premium_active(user_id):
        await message.answer("❌ Bu funksiya faqat Premium userlar uchun!", reply_markup=main_kb)
        return

    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]

    await db.stop_user_campaigns(user_id)

    handler = get_or_create_handler(user_id)
    await handler.stop_campaign(user_id)

    await message.answer(
        "⏹ Xabar yuborish to'xtatildi.\n\n"
        "Qayta boshlash uchun '📤 Xabar yuborish' tugmasini bosing.",
        reply_markup=premium_kb
    )


@router.message(F.text == "📵 Telegram akkauntni uzish")
async def logout_session(message: Message):
    user_id = message.from_user.id

    if not await db.is_premium_active(user_id):
        await message.answer("❌ Bu funksiya faqat Premium userlar uchun!", reply_markup=main_kb)
        return

    session = await db.get_user_session(user_id)
    if not session:
        await message.answer(
            "ℹ️ Sizda hali ulangan akkaunt yo'q.\n\n"
            "Ulanish uchun '📤 Xabar yuborish' tugmasini bosing.",
            reply_markup=premium_kb
        )
        return

    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]

    await db.stop_user_campaigns(user_id)
    await db.delete_user_session(user_id)
    await cleanup_handler(user_id)

    await message.answer(
        "🚪 Session o'chirildi.\n\n"
        "Qayta ulanish uchun '📤 Xabar yuborish' tugmasini bosing.",
        reply_markup=premium_kb
    )
