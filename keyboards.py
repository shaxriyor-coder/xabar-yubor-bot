"""Botning barcha klaviaturalari (Reply va Inline) shu yerda to'planган."""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ===== Oddiy foydalanuvchi =====
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Bu bot haqida")],
        [KeyboardButton(text="ℹ️ Men haqimda")],
        [KeyboardButton(text="🎁 Premium olish")]
    ],
    resize_keyboard=True
)

# ===== Premium foydalanuvchi =====
premium_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Xabar yuborish")],
        [KeyboardButton(text="📵 Telegram akkauntni uzish")],
        [KeyboardButton(text="📝 Bu bot haqida")],
        [KeyboardButton(text="ℹ️ Men haqimda")],
        [KeyboardButton(text="📝 Premium haqida")]
    ],
    resize_keyboard=True
)

# Kampaniya (xabar yuborish) davomida ko'rsatiladigan tugmalar
campaign_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Kampaniyani to'xtatish")],
        [KeyboardButton(text="📵 Telegram akkauntni uzish")],
        [KeyboardButton(text="📝 Premium haqida")]
    ],
    resize_keyboard=True
)

# ===== Admin =====
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Premium userlar ro'yxati")],
        [KeyboardButton(text="🔍 User qidirish")],
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Barcha userlarga xabar yuborish")],
        [KeyboardButton(text="💎 Premium userlarga xabar")],
        [KeyboardButton(text="🗂 Majburiy kanallar")]
    ],
    resize_keyboard=True
)

admin_channel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kanal qo'shish")],
        [KeyboardButton(text="➖ Kanal o'chirish")],
        [KeyboardButton(text="📋 Kanallar ro'yxati")],
        [KeyboardButton(text="⬅️ Ortga")]
    ],
    resize_keyboard=True
)

broadcast_confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Yuborish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)

# Matn/raqam kiritish so'ralganda ko'rsatiladi - foydalanuvchi istalgan vaqtda
# jarayonni bekor qilib, asosiy menyuga qaytishi mumkin bo'lishi uchun
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True
)

# ===== Login usulini tanlash (QR yoki telefon) =====
login_choice_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📷 QR kod orqali", callback_data="login_qr")],
    [InlineKeyboardButton(text="📱 Telefon raqam orqali", callback_data="login_phone")]
])
