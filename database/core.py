"""
Database klassi - PostgreSQL bilan barcha ishlar shu yerdan boshlanadi.

Har bir mavzu (userlar, sessiyalar, kampaniyalar, kanallar, to'lovlar) o'z
faylida (users.py, sessions.py, campaigns.py, channels.py, payments.py)
alohida saqlanadi. Bu klass ularning barchasini birlashtiradi (mixin orqali),
shunda boshqa fayllarda avvalgidek `db.is_premium_active(...)`,
`db.save_user_session(...)` kabi chaqiruvlar o'zgarishsiz ishlayveradi.
"""

import os

import asyncpg
from dotenv import load_dotenv

from .campaigns import CampaignsMixin
from .channels import ChannelsMixin
from .payments import PaymentsMixin
from .sessions import SessionsMixin
from .users import UsersMixin

load_dotenv()


class Database(UsersMixin, SessionsMixin, CampaignsMixin, ChannelsMixin, PaymentsMixin):
    def __init__(self):
        self.pool = None
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }

    async def connect(self):
        """Database'ga ulanish"""
        try:
            self.pool = await asyncpg.create_pool(**self.db_config)
            await self.create_tables()
            print("✅ PostgreSQL'ga ulanish muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Database'ga ulanishda xatolik: {e}")
            raise

    async def create_tables(self):
        """Barcha jadvallarni yaratish"""
        async with self.pool.acquire() as conn:
            await self._create_users_table(conn)
            await self._create_payments_tables(conn)
            await self._create_sessions_table(conn)
            await self._create_campaigns_tables(conn)
            await self._create_channels_table(conn)

    async def get_bot_statistics(self) -> dict:
        """Bot statistikasi (bir nechta jadvaldan yig'ilgan umumiy ma'lumot)"""
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval('SELECT COUNT(*) FROM users') or 0

            premium_users = await conn.fetchval('''
                SELECT COUNT(*) FROM users
                WHERE premium_expiry > extract(epoch from now())
            ''') or 0

            active_campaigns = await conn.fetchval('''
                SELECT COUNT(*) FROM campaigns WHERE is_active = TRUE
            ''') or 0

            total_sent = await conn.fetchval('''
                SELECT SUM(sent_count) FROM campaign_stats
            ''') or 0

            total_failed = await conn.fetchval('''
                SELECT SUM(failed_count) FROM campaign_stats
            ''') or 0

            return {
                'total_users': total_users,
                'premium_users': premium_users,
                'active_campaigns': active_campaigns,
                'total_sent': total_sent,
                'total_failed': total_failed
            }
