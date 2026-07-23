"""user_sessions jadvali: foydalanuvchiga ulangan Telegram akkaunt (Telethon session)."""

from typing import Dict, Optional


class SessionsMixin:
    async def _create_sessions_table(self, conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id BIGINT PRIMARY KEY,
                phone VARCHAR(20) NOT NULL,
                session_string TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at BIGINT DEFAULT extract(epoch from now())
            )
        ''')

    async def save_user_session(self, user_id: int, phone: str, session_string: str):
        """Foydalanuvchi sessiyasini saqlash"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_sessions (user_id, phone, session_string, is_active)
                VALUES ($1, $2, $3, TRUE)
                ON CONFLICT (user_id) DO UPDATE
                SET phone = $2, session_string = $3, is_active = TRUE
            ''', user_id, phone, session_string)

    async def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi sessiyasini olish"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT phone, session_string, is_active FROM user_sessions WHERE user_id = $1',
                user_id
            )
            if row:
                return {
                    'phone': row['phone'],
                    'session_string': row['session_string'],
                    'is_active': row['is_active']
                }
            return None

    async def delete_user_session(self, user_id: int):
        """Foydalanuvchi sessiyasini o'chirish"""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM user_sessions WHERE user_id = $1', user_id)

    async def deactivate_session(self, user_id: int):
        """Sessiyani faolsizlantirish"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE user_sessions SET is_active = FALSE WHERE user_id = $1',
                user_id
            )
