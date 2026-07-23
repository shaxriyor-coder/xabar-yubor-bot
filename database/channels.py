"""required_channels jadvali: Premium olish uchun majburiy obuna kanallari."""

from typing import Dict, List, Optional


class ChannelsMixin:
    async def _create_channels_table(self, conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS required_channels (
                id SERIAL PRIMARY KEY,
                channel_id BIGINT NOT NULL UNIQUE,
                channel_username VARCHAR(255),
                title TEXT NOT NULL,
                added_at BIGINT DEFAULT extract(epoch from now())
            )
        ''')

    async def add_required_channel(self, channel_id: int, channel_username: Optional[str], title: str):
        """Premium uchun majburiy kanal qo'shish"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO required_channels (channel_id, channel_username, title)
                VALUES ($1, $2, $3)
                ON CONFLICT (channel_id) DO UPDATE SET channel_username = $2, title = $3
            ''', channel_id, channel_username, title)

    async def remove_required_channel(self, channel_id: int):
        """Majburiy kanalni ro'yxatdan o'chirish"""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM required_channels WHERE channel_id = $1', channel_id)

    async def get_all_required_channels(self) -> List[Dict]:
        """Barcha majburiy kanallarni olish"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, channel_id, channel_username, title
                FROM required_channels
                ORDER BY added_at ASC
            ''')
            return [dict(row) for row in rows]
