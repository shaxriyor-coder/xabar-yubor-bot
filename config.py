import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 1-Admin (asosiy admin)
ADMIN_ID = int(os.getenv('ADMIN_ID'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')

# 2-Admin (qo'shimcha admin)
ADMIN_ID2_STR = os.getenv('ADMIN_ID2', '0')
ADMIN_ID2 = int(ADMIN_ID2_STR) if ADMIN_ID2_STR and ADMIN_ID2_STR != '0' else 0
ADMIN_USERNAME2 = os.getenv('ADMIN_USERNAME2', '')

# Telegram API
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Database
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# To'lov
CARD_NUMBER = os.getenv('CARD_NUMBER')
PREMIUM_PRICE = os.getenv('PREMIUM_PRICE', '50000')

# Xabar yuborish sozlamalari
MESSAGE_INTERVAL = 5  # 5 sekund
REMINDER_INTERVAL = 30 * 60  # 30 minut (sekundda)