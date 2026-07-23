"""
pending_payments / cooldowns jadvallari - karta orqali to'lov qabul qilish uchun eski funksiyalar.

Hozircha bot.py da bu oqim ISHLATILMAYAPTI - Premium endi bepul, majburiy
obuna orqali beriladi (handlers/premium.py'ga qarang). Bu metodlar kerak
bo'lib qolsa (to'lov tizimini qayta yoqsangiz) tayyor turadi.
"""

import time
from typing import Optional


class PaymentsMixin:
    async def _create_payments_tables(self, conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                user_id BIGINT PRIMARY KEY,
                rejected_count INT DEFAULT 0,
                created_at BIGINT DEFAULT extract(epoch from now())
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id BIGINT PRIMARY KEY,
                expires_at BIGINT NOT NULL
            )
        ''')

    async def add_pending_payment(self, user_id: int):
        """Kutilayotgan to'lovga qo'shish"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO pending_payments (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id)

    async def is_payment_pending(self, user_id: int) -> bool:
        """To'lov kutilayotganligini tekshirish"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT 1 FROM pending_payments WHERE user_id = $1',
                user_id
            )
            return result is not None

    async def remove_pending_payment(self, user_id: int):
        """Kutilayotgan to'lovni o'chirish"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM pending_payments WHERE user_id = $1',
                user_id
            )

    async def get_rejected_count(self, user_id: int) -> int:
        """Rad etilganlar sonini olish"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT rejected_count FROM pending_payments WHERE user_id = $1',
                user_id
            )
            return result or 0

    async def increment_rejected_count(self, user_id: int):
        """Rad etilganlar sonini oshirish"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE pending_payments
                SET rejected_count = rejected_count + 1
                WHERE user_id = $1
            ''', user_id)

    async def reset_rejected_count(self, user_id: int):
        """Rad etilganlar sonini 0'lash"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE pending_payments
                SET rejected_count = 0
                WHERE user_id = $1
            ''', user_id)

    async def add_cooldown(self, user_id: int, seconds: int):
        """Cooldown qo'shish"""
        expires_at = int(time.time()) + seconds
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO cooldowns (user_id, expires_at)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET expires_at = $2
            ''', user_id, expires_at)

    async def get_cooldown(self, user_id: int) -> Optional[int]:
        """Cooldown vaqtini olish"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT expires_at FROM cooldowns WHERE user_id = $1',
                user_id
            )
            if result and result > time.time():
                return result
            elif result:
                await conn.execute('DELETE FROM cooldowns WHERE user_id = $1', user_id)
            return None

    async def remove_cooldown(self, user_id: int):
        """Cooldown'ni o'chirish"""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM cooldowns WHERE user_id = $1', user_id)
