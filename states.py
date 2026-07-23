"""Botning barcha FSM (suhbat holati) klasslari shu yerda to'planган."""

from aiogram.fsm.state import State, StatesGroup


class PhoneState(StatesGroup):
    """Telegram akkauntga kirish (telefon+kod yoki QR, va 2FA parol)"""
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa_password = State()


class IntervalState(StatesGroup):
    """Guruhlar orasidagi xabar yuborish intervalini kiritish"""
    waiting_interval = State()


class MessageState(StatesGroup):
    """Yubormoqchi bo'lgan reklama/xabar matnini kutish"""
    waiting_message = State()


class AdminBroadcastState(StatesGroup):
    """Admindan barcha/Premium userlarga xabar yuborish"""
    waiting_broadcast_message = State()


class AdminChannelState(StatesGroup):
    """Majburiy obuna kanallarini qo'shish/o'chirish"""
    waiting_add_channel = State()
    waiting_remove_channel = State()


class AdminSearchState(StatesGroup):
    """Admin panelda user ID bo'yicha qidiruv"""
    waiting_user_id = State()
