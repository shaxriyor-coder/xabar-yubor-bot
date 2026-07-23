"""users jadvali: ro'yxatga olish, Premium berish/tekshirish/olib qo'yish."""

import time
from typing import Dict, List, Optional


class UsersMixin:
    async def _create_users_table(self, conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                premium_expiry BIGINT DEFAULT 0,
                created_at BIGINT DEFAULT extract(epoch from now())
            )
        ''')

    async def register_user(self, user_id: int):
        """Yangi userni ro'yxatga olish (agar mavjud bo'lmasa)"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, premium_expiry, created_at)
                VALUES ($1, 0, extract(epoch from now()))
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id)

    async def add_premium_user(self, user_id: int, days: int = 30):
        """Foydalanuvchiga premium berish"""
        expiry = int(time.time()) + (days * 24 * 3600)
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, premium_expiry)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET premium_expiry = $2
            ''', user_id, expiry)

    async def is_premium_active(self, user_id: int) -> bool:
        """Premium faolligini tekshirish"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT premium_expiry FROM users WHERE user_id = $1',
                user_id
            )
            if result and result > time.time():
                return True
            return False

    async def get_premium_expiry(self, user_id: int) -> int:
        """Premium tugash vaqtini olish"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT premium_expiry FROM users WHERE user_id = $1',
                user_id
            )
            return result or 0

    async def remove_premium(self, user_id: int):
        """Premium'ni butunlay o'chirish - premium_expiry ni 0 ga o'rnatish"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE users
                SET premium_expiry = 0
                WHERE user_id = $1
            ''', user_id)
            print(f"✅ User {user_id} dan Premium olib qo'yildi (premium_expiry = 0)")

    async def get_all_users(self) -> List[Dict]:
        """Barcha userlarni olish"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, premium_expiry, created_at
                FROM users
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in rows]

    async def get_all_premium_users(self) -> List[Dict]:
        """Barcha premium userlarni olish"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, premium_expiry, created_at
                FROM users
                WHERE premium_expiry > extract(epoch from now())
                ORDER BY premium_expiry DESC
            ''')
            return [dict(row) for row in rows]

    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """User ma'lumotlarini olish"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT user_id, premium_expiry, created_at
                FROM users
                WHERE user_id = $1
            ''', user_id)
            if row:
                return dict(row)
            return None
