# Telegram Messaging Automation Bot

**Telegram guruhlari uchun xabar yuborishni boshqaruvchi bot**

[English](#english) | [O'zbekcha](#ozbekcha)

---

## English

An asynchronous Telegram bot for managing recurring, user-authorized messages to selected Telegram groups. Users sign in with their own Telegram account, choose groups from a chat folder named `Xabar`, and manage a message campaign through a Telegram bot interface. The project also includes subscription checks, premium access, campaign statistics, and administrator tools.

> **Responsible use:** Use this software only with accounts and groups you are authorized to access, and only for messages recipients expect. Follow Telegram's Terms of Service, API terms, and applicable laws. Unsolicited or repetitive messaging can lead to account restrictions.

### Features

- **Telegram bot interface:** Built with aiogram 3 and finite-state workflows for multi-step interactions.
- **Account sign-in:** QR-code or phone/code authentication, including two-factor authentication.
- **Explicit group selection:** Reads groups from the signed-in user's Telegram chat folder named `Xabar`; broadcast channels are excluded.
- **Campaign controls:** Sends recurring text messages; requires a minimum configured interval of 17 seconds and supports manual stop.
- **Premium access:** Grants 30-day access after configured required-channel membership checks; if no required channels are configured, access is granted directly.
- **Admin tools:** User search and statistics, premium management, required-channel management, and confirmed broadcasts to bot users.
- **Persistence:** Stores users, Telegram sessions, campaigns, campaign statistics, and required channels in PostgreSQL.
- **Session lifecycle:** Tracks active user sessions and allows a user to disconnect their linked account from the bot.

### Tech stack

| Area | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Telegram bot API | aiogram 3.10 |
| Telegram client API | Telethon 1.44 |
| Database | PostgreSQL with asyncpg |
| Configuration | `python-dotenv` and environment variables |
| QR generation | `qrcode` and Pillow |

### Architecture

```text
bot.py                 Application entry point and polling lifecycle
config.py              Environment-based configuration
loader.py              Bot, dispatcher, and shared runtime state
handlers/
  common.py             Start, profile, and shared navigation
  login.py              QR, phone/code, and 2FA sign-in
  messaging.py          Campaign setup, start/stop, and account disconnect
  premium.py            Premium access and channel-membership checks
  admin/                User, channel, and broadcast administration
database/
  core.py               PostgreSQL pool and schema initialization
  users.py              User registration and premium access
  sessions.py           Linked Telegram session persistence
  campaigns.py          Campaigns and delivery statistics
  channels.py           Required-channel configuration
  payments.py           Legacy payment/cooldown data methods
user_login.py           Telethon client, group discovery, and campaign runtime
states.py               aiogram conversation states
keyboards.py            Telegram reply and inline keyboards
utils.py                QR image and shared helpers
```

### Requirements

- Python 3.11 or newer
- PostgreSQL
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Telegram API ID and API hash from [my.telegram.org](https://my.telegram.org)
- A Telegram bot administrator account ID

The bot creates its tables when it connects to the configured PostgreSQL database. The database and its credentials must be provisioned separately.

### Setup

1. Clone the repository and enter its directory.

   ```bash
   git clone https://github.com/shaxriyor-coder/xabar-yubor-bot.git
   cd xabar-yubor-bot
   ```

2. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install the pinned dependencies.

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in the required credentials and database settings. Never commit the populated `.env` file.

5. Create a PostgreSQL database and user, then grant the user permission to create tables in that database.

6. Start the bot:

   ```bash
   python bot.py
   ```

### Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token issued by BotFather |
| `ADMIN_ID` | Yes | Telegram numeric user ID for the primary administrator |
| `ADMIN_USERNAME` | Recommended | Administrator username used by the contact link |
| `API_ID` | Yes | Telegram application API ID |
| `API_HASH` | Yes | Telegram application API hash |
| `DB_HOST` | No | PostgreSQL host; defaults to `localhost` |
| `DB_PORT` | No | PostgreSQL port; defaults to `5432` |
| `DB_NAME` | Yes | Existing PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL username |
| `DB_PASSWORD` | Yes | PostgreSQL password |

The active runtime reads `ADMIN_ID` as its administrator. Although `ADMIN_ID2` and `ADMIN_USERNAME2` are parsed by the configuration module, a second administrator is not enabled in the current runtime configuration. `CARD_NUMBER` and `PREMIUM_PRICE` belong to the inactive legacy payment flow and have no effect on the current bot.

### Basic user flow

1. Start the bot with `/start`.
2. Use **Premium olish** to obtain access. If required channels are configured, join them and request membership verification; if none are configured, the bot grants access directly.
3. Create a Telegram chat folder named `Xabar` and add only groups where you are permitted to post.
4. Start **Xabar yuborish** and link your own account using QR or phone verification.
5. Choose an interval of at least 17 seconds, then submit the text to send.
6. Use **Kampaniyani to'xtatish** to stop a running campaign or **Telegram akkauntni uzish** to remove the linked session.

Administrators can manage required channels and premium users, inspect usage statistics, and send a bot broadcast (text, photo, video, or document) after confirming the recipients and message.

### Security and operational notes

- Treat `BOT_TOKEN`, `API_HASH`, database credentials, phone numbers, and Telegram session strings as secrets. Do not put them in source control, screenshots, logs, or public issue reports.
- Telegram session strings are persisted in PostgreSQL by the current implementation. Restrict database access, use encrypted connections and protected backups, and do not expose production database contents.
- Use a private, access-controlled PostgreSQL instance and a dedicated database account with only the permissions the bot needs.
- Revoke a linked Telegram session from Telegram's **Settings → Devices** if it may have been exposed. The bot also provides an account-disconnect action.
- Configure the bot as an administrator in each required channel so it can verify membership.
- There is no automated test suite in the repository at this time.

### Resume-ready summary

- Built an asynchronous Telegram bot with aiogram and Telethon, including QR/phone authentication, 2FA handling, and PostgreSQL-backed user sessions.
- Implemented campaign and subscription workflows, administrator tools, and persistent user, channel, and delivery-statistics data models.

---

## O'zbekcha

Tanlangan Telegram guruhlariga xabar kampaniyalarini boshqarish uchun Python’da yozilgan asinxron Telegram bot. Foydalanuvchi o'z Telegram akkauntini ulaydi, `Xabar` nomli suhbat jildidagi guruhlarni tanlaydi va xabar kampaniyasini bot orqali boshqaradi. Loyihada Premium obuna, majburiy kanal a'zoligini tekshirish, statistika va administrator vositalari ham mavjud.

> **Mas'uliyatli foydalanish:** Dasturdan faqat o'zingiz foydalanishga haqli bo'lgan akkaunt va guruhlarda, qabul qiluvchilar kutayotgan xabarlar uchun foydalaning. Telegram foydalanish shartlari, API qoidalari va mahalliy qonunlarga rioya qiling. Ruxsatsiz yoki takroriy xabarlar akkaunt cheklanishiga olib kelishi mumkin.

### Imkoniyatlar

- **Telegram bot interfeysi:** aiogram 3 va ko'p bosqichli FSM suhbat jarayonlari.
- **Akkauntga kirish:** QR kod yoki telefon raqami/kod orqali kirish, 2FA qo'llab-quvvatlovi bilan.
- **Guruhlarni aniq tanlash:** Ulangan akkauntdagi `Xabar` nomli suhbat jildidan guruhlarni oladi; kanal turlari chiqarib tashlanadi.
- **Kampaniya boshqaruvi:** Matnli xabarni takroran yuborish; eng kam interval 17 soniya; kampaniyani qo'lda to'xtatish.
- **Premium:** Sozlangan majburiy kanallarga a'zolik tekshirilgach, 30 kunlik kirish huquqini beradi; majburiy kanal bo'lmasa, kirish to'g'ridan-to'g'ri beriladi.
- **Admin vositalari:** Foydalanuvchilar va statistika, Premium boshqaruvi, majburiy kanallar hamda tasdiqlanadigan ommaviy xabarlar.
- **Ma'lumotlarni saqlash:** Foydalanuvchilar, Telegram sessiyalari, kampaniyalar, yuborish statistikasi va kanallar PostgreSQL’da saqlanadi.
- **Sessiya boshqaruvi:** Ulangan akkaunt sessiyasini kuzatish va bot orqali uzish imkoniyati.

### Texnologiyalar

| Yo'nalish | Texnologiya |
| --- | --- |
| Dasturlash tili | Python 3.11+ |
| Telegram bot API | aiogram 3.10 |
| Telegram client API | Telethon 1.44 |
| Ma'lumotlar bazasi | asyncpg orqali PostgreSQL |
| Sozlamalar | `python-dotenv` va environment variables |
| QR kod | `qrcode` va Pillow |

### Arxitektura

Yuqoridagi **Architecture** bo'limida loyiha kataloglari va modullari ro'yxati berilgan: `handlers/` buyruq va suhbat oqimlari, `database/` PostgreSQL amallari, `user_login.py` Telethon akkaunt hamda kampaniya jarayonlari uchun mas'ul.

### Talablar

- Python 3.11 yoki undan yangi
- PostgreSQL
- [@BotFather](https://t.me/BotFather)-dan olingan Telegram bot token
- [my.telegram.org](https://my.telegram.org)-dan olingan Telegram API ID va API hash
- Asosiy administratorning Telegram raqamli user ID raqami

Bot PostgreSQL’ga ulanganda jadvallarni o'zi yaratadi. Ma'lumotlar bazasi va unga ulanish ma'lumotlarini alohida tayyorlash kerak.

### O'rnatish va ishga tushirish

1. Repozitoriyani klonlab, loyiha katalogiga o'ting:

   ```bash
   git clone https://github.com/shaxriyor-coder/xabar-yubor-bot.git
   cd xabar-yubor-bot
   ```

2. Virtual muhit yarating va faollashtiring:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell: `.\.venv\Scripts\Activate.ps1`

   macOS/Linux: `source .venv/bin/activate`

3. Bog'liqliklarni o'rnating:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. `.env.example` faylidan `.env` nusxasini yarating va kerakli token, API hamda PostgreSQL sozlamalarini kiriting. Haqiqiy `.env` faylini Git’ga hech qachon qo'shmang.

5. PostgreSQL’da baza va foydalanuvchi yarating; botga jadvallar yaratish huquqini bering.

6. Botni ishga tushiring:

   ```bash
   python bot.py
   ```

### Muhit o'zgaruvchilari

Yuqoridagi **Configuration** jadvalida barcha o'zgaruvchilar, majburiyligi va standart qiymatlari keltirilgan. `BOT_TOKEN`, `ADMIN_ID`, `API_ID`, `API_HASH`, `DB_NAME`, `DB_USER` va `DB_PASSWORD` qiymatlarini `.env` faylida belgilang. `DB_HOST` va `DB_PORT` ixtiyoriy; standart qiymatlari `localhost` va `5432`.

Joriy runtime faqat `ADMIN_ID`ni administrator sifatida ishlatadi. `ADMIN_ID2` va `ADMIN_USERNAME2` konfiguratsiyada o'qilsa-da, ikkinchi admin hozirgi runtime’da yoqilmagan. `CARD_NUMBER` va `PREMIUM_PRICE` qiymatlari faol bo'lmagan eski to'lov oqimiga tegishli va botning joriy ishlashiga ta'sir qilmaydi.

### Foydalanish

1. Botni `/start` buyrug'i bilan boshlang.
2. **Premium olish** orqali kirish huquqini oling. Majburiy kanallar sozlangan bo'lsa, ularga a'zo bo'lib tekshiruvni so'rang; kanal sozlanmagan bo'lsa, bot kirishni bevosita beradi.
3. Telegram’da `Xabar` nomli suhbat jildini yarating va faqat xabar yuborishga ruxsatingiz bor guruhlarni qo'shing.
4. **Xabar yuborish**ni tanlab, o'z akkauntingizni QR yoki telefon orqali ulang.
5. Kamida 17 soniyalik interval kiriting va matnli xabar yuboring.
6. Kampaniyani **Kampaniyani to'xtatish** bilan to'xtating yoki **Telegram akkauntni uzish** orqali sessiyani o'chiring.

Administratorlar majburiy kanallar va Premium foydalanuvchilarini boshqarishi, statistikani ko'rishi hamda qabul qiluvchilar va xabarni tasdiqlagandan so'ng bot orqali matn, rasm, video yoki hujjat yuborishi mumkin.

### Xavfsizlik va ekspluatatsiya

- `BOT_TOKEN`, `API_HASH`, baza parollari, telefon raqamlari va Telegram sessiya satrlarini maxfiy saqlang. Ularni Git’ga, skrinshotlarga, loglarga yoki ochiq issue’larga joylamang.
- Joriy kod Telegram sessiya satrlarini PostgreSQL’da saqlaydi. Baza kirishini cheklang, shifrlangan ulanish va himoyalangan zaxira nusxalaridan foydalaning; production bazasini oshkor qilmang.
- Bot uchun alohida, minimal zarur huquqlarga ega PostgreSQL foydalanuvchisi va kirishi cheklangan baza ishlating.
- Sessiya oshkor bo'lishi mumkin bo'lsa, Telegram **Settings → Devices** orqali uni bekor qiling. Botda akkauntni uzish tugmasi ham mavjud.
- A'zolik tekshiruvi ishlashi uchun botni har bir majburiy kanalga administrator qilib qo'shing.
- Repozitoriyada hozircha avtomatlashtirilgan testlar mavjud emas.
