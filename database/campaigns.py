"""campaigns / campaign_stats jadvallari: xabar yuborish kampaniyalari."""

from typing import Dict, List, Optional


class CampaignsMixin:
    async def _create_campaigns_tables(self, conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                message_text TEXT NOT NULL,
                group_ids BIGINT[] NOT NULL,
                interval_seconds INTEGER DEFAULT 17,
                is_active BOOLEAN DEFAULT TRUE,
                created_at BIGINT DEFAULT extract(epoch from now()),
                last_reminder BIGINT DEFAULT extract(epoch from now())
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS campaign_stats (
                campaign_id INT REFERENCES campaigns(id),
                sent_count INT DEFAULT 0,
                failed_count INT DEFAULT 0,
                last_sent_at BIGINT DEFAULT 0,
                PRIMARY KEY (campaign_id)
            )
        ''')

        try:
            await conn.execute('''
                ALTER TABLE campaigns
                ADD COLUMN IF NOT EXISTS interval_seconds INTEGER DEFAULT 17
            ''')
        except Exception as e:
            print(f"⚠️ campaigns jadvalini yangilashda xatolik: {e}")

    async def create_campaign(
        self,
        user_id: int,
        message_text: str,
        group_ids: List[int],
        interval: int = 17,
        message_type: str = "text",
        file_id: Optional[str] = None
    ) -> int:
        """Yangi kampaniya yaratish (avvalgi faol kampaniyalar to'xtatiladi)"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE campaigns SET is_active = FALSE WHERE user_id = $1',
                user_id
            )

            campaign_id = await conn.fetchval('''
                INSERT INTO campaigns (user_id, message_text, group_ids, interval_seconds, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                RETURNING id
            ''', user_id, message_text, group_ids, interval)

            await conn.execute('''
                INSERT INTO campaign_stats (campaign_id)
                VALUES ($1)
            ''', campaign_id)

            return campaign_id

    async def get_campaign_by_id(self, campaign_id: int) -> Optional[Dict]:
        """Kampaniya ma'lumotlarini ID bo'yicha olish"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, user_id, message_text, group_ids, interval_seconds, is_active
                FROM campaigns
                WHERE id = $1
            ''', campaign_id)

            if row:
                return {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'message_text': row['message_text'],
                    'group_ids': row['group_ids'],
                    'interval': row.get('interval_seconds', 17),
                    'is_active': row['is_active']
                }
            return None

    async def get_active_campaign(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchining faol kampaniyasini olish"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, message_text, group_ids, interval_seconds, last_reminder
                FROM campaigns
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            ''', user_id)

            if row:
                return {
                    'id': row['id'],
                    'message_text': row['message_text'],
                    'group_ids': row['group_ids'],
                    'interval': row.get('interval_seconds', 17),
                    'last_reminder': row['last_reminder']
                }
            return None

    async def stop_user_campaigns(self, user_id: int):
        """Foydalanuvchining barcha kampaniyalarini to'xtatish"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE campaigns SET is_active = FALSE WHERE user_id = $1',
                user_id
            )

    async def update_campaign_stats(self, campaign_id: int, sent: int = 0, failed: int = 0):
        """Kampaniya statistikasini yangilash"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE campaign_stats
                SET sent_count = sent_count + $2,
                    failed_count = failed_count + $3,
                    last_sent_at = extract(epoch from now())
                WHERE campaign_id = $1
            ''', campaign_id, sent, failed)

    async def update_campaign_reminder(self, campaign_id: int):
        """Kampaniya eslatma vaqtini yangilash"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE campaigns
                SET last_reminder = extract(epoch from now())
                WHERE id = $1
            ''', campaign_id)
