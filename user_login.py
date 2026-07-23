import asyncio
import random
import time
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    FloodWaitError,
    SessionRevokedError,
    AuthKeyUnregisteredError,
    UserDeactivatedError,
    UserDeactivatedBanError,
    ChatWriteForbiddenError,
    ChatAdminRequiredError,
    UserBannedInChannelError,
    PeerIdInvalidError,
    ChatIdInvalidError,
    MessageTooLongError,
    FileReferenceExpiredError
)
from telethon.tl.functions.messages import GetDialogFiltersRequest
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')

class UserBotHandler:
    """Har bir user uchun alohida Telegram client bilan ishlaydi"""
    
    def __init__(self, bot_instance=None, user_id: Optional[int] = None):
        self.user_id = user_id
        self.client: Optional[TelegramClient] = None
        self.pending_client: Optional[TelegramClient] = None
        self.pending_qr_login = None  # QR orqali login jarayonidagi obyekt
        self.is_campaign_active = False
        self.campaign_task: Optional[asyncio.Task] = None
        self.bot = bot_instance
        
        # HAR GURUH UCHUN INDEPENDENT STATE - har bir guruh o'z intervalida,
        # bir-biriga bog'liq bo'lmagan holda ishlaydi (pastda tushuntirilgan)
        self.group_tasks = {}
        self.group_states = {}

        # ULANISH (INTERNET) HOLATINI KUZATISH
        self.connection_lost_notified = False

        # SESSIYANI FONDA KUZATISH (kampaniya ishlamayotgan bo'lsa ham)
        self.session_watch_task: Optional[asyncio.Task] = None
        self._session_watch_active = False

        print(f"✅ UserBotHandler yaratildi (user_id: {user_id})")
    
    async def start(self):
        """Handler'ni ishga tushirish"""
        print(f"✅ UserBotHandler tayyor (user_id: {self.user_id})")
    
    async def stop(self):
        """Handler'ni to'xtatish va clientlarni yopish"""
        self.stop_session_watch()

        if self.is_campaign_active:
            await self.stop_campaign(self.user_id)

        for task in self.group_tasks.values():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            print(f"🔌 Client uzildi (user_id: {self.user_id})")
        
        if self.pending_client and self.pending_client.is_connected():
            await self.pending_client.disconnect()
            print(f"🔌 Pending client uzildi (user_id: {self.user_id})")
        
        self.client = None
        self.pending_client = None
        self.pending_qr_login = None
        self.connection_lost_notified = False
        self.group_tasks.clear()
        self.group_states.clear()

    async def get_logged_in_phone(self) -> str:
        """Kirilgan akkauntning telefon raqamini olish"""
        if not self.client:
            return ""
        me = await self.client.get_me()
        return me.phone or ""

    def begin_watching_session(self, user_id: int, check_interval: int = 60):
        """
        Login muvaffaqiyatli bo'lgach chaqiriladi - sessiyani fonda kuzatib
        turadigan alohida jarayon boshlanadi.

        Nega kerak: agar foydalanuvchi kampaniya ishga tushirmagan bo'lsa,
        hech kim akkaunt hali ham amal qilib turganini tekshirmaydi. Shu
        sabab, foydalanuvchi akkauntni Telegram'ning o'zidan (Sozlamalar
        → Qurilmalar) uzib tashlasa, bot buni HECH QACHON payqamas edi.
        Bu funksiya har `check_interval` soniyada bir marta tekshirib,
        uzilgan bo'lsa foydalanuvchiga darhol xabar beradi.
        """
        self.stop_session_watch()
        self._session_watch_active = True
        self.session_watch_task = asyncio.create_task(self._watch_session(user_id, check_interval))

    def stop_session_watch(self):
        """Sessiya kuzatuvini to'xtatish"""
        self._session_watch_active = False
        if self.session_watch_task and not self.session_watch_task.done():
            self.session_watch_task.cancel()
        self.session_watch_task = None

    async def _watch_session(self, user_id: int, check_interval: int):
        while self._session_watch_active:
            await asyncio.sleep(check_interval)
            if not self._session_watch_active:
                break

            # Kampaniya ishlab turganda tekshirish shart emas - u yerdagi
            # xatolar allaqachon _handle_group_error orqali ushlanadi
            if self.is_campaign_active:
                continue

            try:
                if self.client and self.client.is_connected():
                    await self.client.get_me()
            except (SessionRevokedError, AuthKeyUnregisteredError, UserDeactivatedError, UserDeactivatedBanError):
                print(f"❌ Sessiya uzilgani aniqlandi (user_id: {user_id})")
                self._session_watch_active = False

                try:
                    from database import db
                    await db.delete_user_session(user_id)
                except Exception as e:
                    print(f"⚠️ Sessiyani bazadan o'chirishda xatolik: {e}")

                if self.bot:
                    try:
                        await self.bot.send_message(
                            user_id,
                            "❌ *Telegram akkauntingiz uzilib qoldi!*\n\n"
                            "Buning sababi Telegram'ning o'zidan (Sozlamalar → Qurilmalar) "
                            "sessiyani tugatgan bo'lishingiz yoki boshqa sabab bo'lishi mumkin.\n\n"
                            "📤 Qayta ulanish uchun '📤 Xabar yuborish' tugmasini bosing.",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

                break
            except Exception as e:
                print(f"⚠️ Sessiya kuzatuvida vaqtinchalik xatolik (user_id: {user_id}): {e}")
                continue

    async def start_qr_login(self, user_id: int) -> str:
        """QR kod orqali login boshlash - skaner qilish uchun havolani qaytaradi"""
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        qr_login = await client.qr_login()
        self.pending_client = client
        self.pending_qr_login = qr_login

        print(f"📷 QR login boshlandi (user_id: {user_id})")
        return qr_login.url

    async def wait_qr_login(self, user_id: int, timeout: int = 60) -> str:
        """Foydalanuvchi QR kodni skaner qilishini kutish, muvaffaqiyatli bo'lsa session_string qaytaradi"""
        if not self.pending_qr_login or not self.pending_client:
            raise Exception("Avval QR kod so'ralishi kerak!")

        qr_login = self.pending_qr_login
        client = self.pending_client

        try:
            await qr_login.wait(timeout=timeout)
            session_string = client.session.save()

            self.client = client
            self.pending_client = None
            self.pending_qr_login = None

            print(f"✅ User {user_id} QR orqali login qildi")
            return session_string

        except SessionPasswordNeededError:
            # 2FA kerak - pending_client saqlanib qoladi, sign_in_with_2fa shu clientdan foydalanadi
            print(f"🔐 User {user_id} uchun 2FA kerak (QR)")
            raise Exception("2FA_REQUIRED")

        except asyncio.TimeoutError:
            await client.disconnect()
            self.pending_client = None
            self.pending_qr_login = None
            raise Exception("QR_TIMEOUT")

        except Exception as e:
            await client.disconnect()
            self.pending_client = None
            self.pending_qr_login = None
            raise Exception(f"QR login xatolik: {str(e)}")

    async def send_code(self, user_id: int, phone: str):
        """Telefon raqamga kod yuborish"""
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.send_code_request(phone)
            self.pending_client = client
            print(f"📱 Kod yuborildi: {phone} (user_id: {user_id})")
        except Exception as e:
            await client.disconnect()
            raise Exception(f"Kod yuborishda xatolik: {str(e)}")
    
    async def sign_in(self, user_id: int, phone: str, code: str) -> str:
        """Kodni tasdiqlash va login qilish"""
        if not self.pending_client:
            raise Exception("Avval telefon raqam yuborilishi kerak!")
        
        client = self.pending_client
        
        try:
            await client.sign_in(phone, code.replace('.', '').replace(' ', ''))
            session_string = client.session.save()
            
            self.client = client
            self.pending_client = None
            
            print(f"✅ User {user_id} login qildi")
            return session_string
            
        except SessionPasswordNeededError:
            print(f"🔐 User {user_id} uchun 2FA kerak")
            raise Exception("2FA_REQUIRED")
            
        except Exception as e:
            await client.disconnect()
            self.pending_client = None
            raise Exception(f"Login xatolik: {str(e)}")
    
    async def sign_in_with_2fa(self, user_id: int, password: str) -> str:
        """2FA parol bilan login qilish"""
        if not self.pending_client:
            raise Exception("Avval telefon va kod yuborilishi kerak!")
        
        client = self.pending_client
        
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            
            self.client = client
            self.pending_client = None
            
            print(f"✅ User {user_id} 2FA bilan login qildi")
            return session_string
            
        except Exception as e:
            await client.disconnect()
            self.pending_client = None
            raise Exception(f"2FA login xatolik: {str(e)}")
    
    def _get_folder_title(self, folder):
        """Folder nomini xavfsiz tarzda olish"""
        folder_title = getattr(folder, 'title', 'NOM_MAVJUD_EMAS')
        
        if hasattr(folder_title, 'text'):
            folder_title = folder_title.text
        elif not isinstance(folder_title, str):
            folder_title = str(folder_title)
            
        return folder_title
    
    async def _check_session_validity(self, user_id: int, session_string: str) -> bool:
        """Session hali ham amal qilayotganini tekshirish"""
        try:
            if not self.client or not self.client.is_connected():
                self.client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                await self.client.connect()
            
            await self.client.get_me()
            return True
            
        except (SessionRevokedError, AuthKeyUnregisteredError):
            print(f"❌ Session bekor qilingan (user_id: {user_id})")
            return False
        except (UserDeactivatedError, UserDeactivatedBanError):
            print(f"❌ Akkaunt o'chirilgan/bloklangan (user_id: {user_id})")
            return False
        except Exception as e:
            print(f"⚠️ Session tekshirishda xatolik: {e}")
            return False
    
    async def get_groups_from_folder(self, user_id: int, session_string: str, folder_name: str = "Xabar") -> List[Dict]:
        """Foydalanuvchining ma'lum jildidagi FAQAT GURUHLARNI olish (kanallarni emas!)"""
        is_valid = await self._check_session_validity(user_id, session_string)
        if not is_valid:
            raise Exception("SESSION_INVALID: Session bekor qilingan. Iltimos, qayta login qiling.")
        
        print(f"🔍 '{folder_name}' jildini qidiryapman... (user_id: {user_id})")
        
        try:
            result = await self.client(GetDialogFiltersRequest())
            # Telethon versiyasiga qarab natija ikki xil qaytishi mumkin:
            # eski versiyalarda oddiy list (Vector<DialogFilter>), yangilarida
            # esa `.filters` atributiga ega obyekt (messages.DialogFilters).
            # Faqat `.filters` ni tekshirish eski versiyada doim bo'sh []
            # qaytarardi - shuning uchun mavjud jild ham "topilmadi" bo'lardi.
            if hasattr(result, 'filters'):
                folders = result.filters
            elif isinstance(result, list):
                folders = result
            else:
                folders = []

            print(f"📁 Jami {len(folders)} ta folder topildi")
            
            target_folder = None
            for folder in folders:
                folder_title = self._get_folder_title(folder)
                
                if folder_title and isinstance(folder_title, str) and folder_title.strip().lower() == folder_name.strip().lower():
                    target_folder = folder
                    print(f"✅ TARGET FOLDER TOPILDI: '{folder_title}'")
                    break
            
            groups = []
            
            if target_folder and hasattr(target_folder, 'include_peers'):
                print(f"🎯 '{folder_name}' jildidagi FAQAT GURUHLARNI olish...")
                
                for peer in target_folder.include_peers:
                    try:
                        entity = await self.client.get_entity(peer)
                        
                        is_group = hasattr(entity, 'megagroup') and entity.megagroup
                        is_supergroup = hasattr(entity, 'title') and hasattr(entity, 'participants_count') and not (hasattr(entity, 'broadcast') and entity.broadcast)
                        is_channel = hasattr(entity, 'broadcast') and entity.broadcast
                        
                        if (is_group or is_supergroup) and not is_channel:
                            title = getattr(entity, 'title', 'Nomsiz guruh')
                            username = getattr(entity, 'username', None)
                            
                            groups.append({
                                'id': entity.id,
                                'title': title,
                                'username': username,
                                'type': 'group'
                            })
                            print(f"  ✅ GURUH: {title}")
                        elif is_channel:
                            title = getattr(entity, 'title', 'Nomsiz')
                            print(f"  ⚠️ KANAL O'TKAZIB YUBORILDI: {title}")
                            
                    except Exception as e:
                        print(f"  ⚠️ {peer} xatolik: {e}")
            
            if not groups:
                print("🔄 Folder topilmadi yoki guruh yo'q.")
            
            print(f"📊 Natija: {len(groups)} ta GURUH topildi")
            return groups
            
        except Exception as e:
            print(f"❌ Xatolik: {e}")
            return []
    
    async def _handle_send_error(self, error: Exception, group_id: int, user_id: int) -> tuple:
        """Xabar yuborishdagi xatolarni handle qilish"""
        error_str = str(error)
        
        if isinstance(error, (SessionRevokedError, AuthKeyUnregisteredError)):
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        "❌ *Session bekor qilingan!*\n\n"
                        "📱 Iltimos, '📵 Telegram akkauntni uzish' tugmasini bosib, qayta login qiling.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            return ("session_revoked", "Session bekor qilingan")
        
        elif isinstance(error, ChatWriteForbiddenError):
            return ("forbidden", f"Guruh {group_id} da yozish huquqi yo'q")
        
        elif isinstance(error, ChatAdminRequiredError):
            return ("admin_required", f"Guruh {group_id} da admin huquqi kerak")
        
        elif isinstance(error, UserBannedInChannelError):
            return ("banned", f"Guruh {group_id} da ban olgan")
        
        elif isinstance(error, (PeerIdInvalidError, ChatIdInvalidError)):
            return ("invalid_id", f"Guruh {group_id} topilmadi")
        
        elif isinstance(error, FloodWaitError):
            return ("flood_wait", error.seconds)
        
        elif isinstance(error, (UserDeactivatedError, UserDeactivatedBanError)):
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        "❌ *Akkaunt o'chirilgan!*\n\n"
                        "📱 Iltimos, yangi akkaunt bilan login qiling.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            return ("account_deleted", "Akkaunt o'chirilgan")
        
        elif isinstance(error, MessageTooLongError):
            return ("message_too_long", "Xabar juda uzun")
        
        elif isinstance(error, FileReferenceExpiredError):
            return ("file_expired", "Fayl havolasi eskirgan")
        
        else:
            if "A wait of" in error_str and "seconds" in error_str:
                import re
                match = re.search(r'wait of (\d+) seconds', error_str)
                if match:
                    seconds = int(match.group(1))
                    return ("flood_wait", seconds)
            
            return ("unknown", error_str)

    async def _handle_group_error(self, error: Exception, user_id: int, campaign_id: int, group_id: int, state: dict):
        """Guruh xatosini handle qilish - FAQAT SHU GURUH UCHUN"""
        error_type, error_data = await self._handle_send_error(error, group_id, user_id)
        
        # Session yoki akkaunt xatolari - BUTUN KAMPANIYA TO'XTATILADI
        if error_type in ["session_revoked", "account_deleted"]:
            print("  🔴 SESSION XATOSI! Butun kampaniya to'xtatiladi")
            self.is_campaign_active = False
            
            try:
                from database import db
                await db.stop_user_campaigns(user_id)
            except Exception as e:
                print(f"  ⚠️ DB kampaniya to'xtatish xatolik: {e}")
            
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        "❌ *Session bekor qilingan!*\n\n"
                        "Iltimos, '📵 Telegram akkauntni uzish' tugmasini bosib, qayta login qiling.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            
            return
        
        # Flood wait - Telegram AYNAN SHU GURUH uchun cheklov qo'ydi.
        # Faqat shu guruhning intervalini oshiramiz - boshqa guruhlarga tegmaydi,
        # ular o'zining eski (yoki boshqa sababdan boshqacha) intervalida davom etadi.
        elif error_type == "flood_wait":
            flood_seconds = error_data
            user_interval = state['user_interval']
            new_interval = flood_seconds + user_interval

            state['current_interval'] = new_interval
            state['flood_wait_until'] = time.time() + flood_seconds

            minutes = new_interval // 60
            secs = new_interval % 60

            print(f"  🔴 GURUH {group_id} CHEKLANDI!")
            print(f"     Yangi interval: {new_interval}s ({minutes}m {secs}s)")
            
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        f"⚠️ Guruh cheklovi!\n\n"
                        f"📛 Guruh: {state.get('group_name', group_id)}\n"
                        f"⏰ Cheklov: {flood_seconds}s\n"
                        f"🔢 Yangi interval: {minutes}m {secs}s\n\n"
                        f"🔄 Guruh cheklanganlar ro'yxatiga o'tkazildi",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        
        # Guruh xatolari - FAQAT SHU GURUH TO'XTATILADI
        elif error_type in ["forbidden", "admin_required", "banned", "invalid_id"]:
            print(f"  ❌ Guruh {group_id}: {error_data} - FAQAT SHU GURUH TO'XTATILDI")
            state['has_error'] = True
            
            group_name = state.get('group_name', f'Guruh {group_id}')
            
            # Xato xabarini tayyorlash
            if error_type == "forbidden":
                error_msg = f"🚫 *Yozish huquqi cheklangan!*\n\n📛 Guruh: *{group_name}*\n\n❌ Bu guruhda xabar yuborish huquqingiz yo'q."
            elif error_type == "admin_required":
                error_msg = f"🚫 *Admin huquqi kerak!*\n\n📛 Guruh: *{group_name}*\n\n❌ Faqat adminlar xabar yubora oladi."
            elif error_type == "banned":
                error_msg = f"🚫 *Siz bloklangansiz!*\n\n📛 Guruh: *{group_name}*\n\n❌ Bu guruhda sizga ban berilgan."
            elif error_type == "invalid_id":
                error_msg = f"🚫 *Guruh topilmadi!*\n\n📛 Guruh: *{group_name}*\n\n❌ Guruh o'chirilgan yoki ID noto'g'ri."
            else:
                error_msg = f"🚫 *Xatolik!*\n\n📛 Guruh: *{group_name}*\n\n❌ {error_data}"
            
            error_msg += "\n\n⏭ *Bu guruh keyingi aylanalarda o'tkazib yuboriladi*"
            
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        error_msg,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            
            try:
                from database import db
                await db.update_campaign_stats(campaign_id, sent=0, failed=1)
            except Exception as e:
                print(f"  ⚠️ Statistika xatolik: {e}")
        
        # Boshqa xatolar
        else:
            print(f"  ❌ Guruh {group_id} noma'lum xatolik: {error_data}")
            
            try:
                from database import db
                await db.update_campaign_stats(campaign_id, sent=0, failed=1)
            except Exception as e:
                print(f"  ⚠️ Statistika xatolik: {e}")

    async def _send_to_group(self, user_id: int, campaign_id: int, group_id: int, message_text: str, state: dict) -> bool:
        """
        Bitta guruhga xabar yuborish - return True agar muvaffaqiyatli.

        Har bir guruh o'zining ALOHIDA asyncio taskida ishlaydi (pastdagi
        _process_single_group), shuning uchun bu yerda boshqa guruhlar bilan
        umumiy lock/navbat SHART EMAS - har bir guruh mustaqil o'z
        `current_interval`'iga qarab yuboradi. Agar Telegram aynan shu guruh
        uchun flood-limit qo'ysa, faqat shu guruhning intervali oshadi
        (_handle_group_error orqali) - boshqa guruhlarga ta'sir qilmaydi.
        """
        current_interval = state['current_interval']
        print(f"  📤 Guruh {group_id} ({current_interval}s interval) yuborilmoqda...")

        try:
            await self.client.send_message(group_id, message_text)

            state['last_sent'] = time.time()

            try:
                from database import db
                await db.update_campaign_stats(campaign_id, sent=1, failed=0)
            except Exception as e:
                print(f"  ⚠️ Statistika xatolik: {e}")

            return True

        except Exception as e:
            await self._handle_group_error(e, user_id, campaign_id, group_id, state)
            return False

    async def _wait_for_connection(self, user_id: int) -> bool:
        """
        Ulanish (internet) yo'qolganda kutish.

        Nega kerak: agar serverning interneti uzilib qolsa, xabar yuborish
        to'xtaydi. Ulanish qayta tiklanganda, barcha guruh tasklari bir xil
        onda uyg'onib, DARHOL xabar yuborishga urinishi mumkin - bu Telegram
        nazarida spam kabi ko'rinib, akkauntni flood/ban qilib qo'yishi mumkin.

        Shuning uchun: ulanish tiklanganda har bir task tasodifiy (0-3 soniya)
        kutib turadi - shu orqali hammasi bir zumda emas, sochilib tarqalgan
        holda davom etadi.
        """
        if self.client and self.client.is_connected():
            return True

        if not self.connection_lost_notified:
            self.connection_lost_notified = True
            print(f"📡 Ulanish yo'q (user_id: {user_id}) - internet tiklanishini kutmoqda...")
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        "📡 *Internet/serverda ulanish uzildi!*\n\n"
                        "Xabar yuborish vaqtincha pauza qilindi.\n"
                        "⚠️ Akkauntingiz bloklanmasligi uchun, ulanish tiklangach xabarlar "
                        "birdaniga emas, to'liq interval bilan qayta boshlanadi.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        while self.is_campaign_active:
            if self.client and self.client.is_connected():
                break
            await asyncio.sleep(5)

        if not self.is_campaign_active:
            return False

        print(f"📡 Ulanish tiklandi (user_id: {user_id})")
        self.connection_lost_notified = False

        # Tasodifiy kutish - barcha guruh tasklari bir zumda emas, sochilib
        # qayta xabar yuborishni boshlashi uchun (portlashning oldini olish)
        await asyncio.sleep(random.uniform(0.5, 3.0))

        return True

    async def _process_single_group(self, user_id: int, campaign_id: int, group_id: int, message_text: str, start_delay: float = 0):
        """
        Bitta guruhni qayta ishlash - DOIMIY SIKL (CHEKSIZ).

        Har bir guruh MUSTAQIL ishlaydi: o'zining `current_interval`'iga qarab
        yuboradi va boshqa guruhlarni kutmaydi. Agar Telegram aynan shu guruh
        uchun flood-limit qo'ysa, faqat shu guruhning intervali oshadi - masalan
        bitta guruh 5 daqiqada, boshqasi hali ham 20 sekundda davom etishi
        mumkin. `start_delay` - barcha guruhlar bir zumda emas, ozgina farq
        bilan boshlanishi uchun (portlab yubormaslik uchun).
        """
        if start_delay:
            await asyncio.sleep(start_delay)

        print(f"🔄 Guruh {group_id} DOIMIY SIKL boshlandi (CHEKSIZ)")

        try:
            # HAR BIR GURUH UCHUN ALOHIDA STATE
            state = self.group_states.get(group_id)
            if not state:
                print(f"❌ Guruh {group_id} uchun state topilmadi")
                return

            send_count = 0
            cycle_count = 0

            while self.is_campaign_active:  # FAQAT SHART: kampaniya faol
                try:
                    cycle_count += 1
                    print(f"  🔄 Guruh {group_id} - {cycle_count}-aylana")

                    # Agar guruhda xato bo'lsa, KEYINGI AYLANAGA O'TISH
                    if state.get('has_error', False):
                        print(f"  ⏭ Guruh {group_id} da xato - keyingi aylanaga o'tiladi")
                        # Xato bo'lgan guruh uchun interval kutish
                        await asyncio.sleep(state.get('user_interval', 20))
                        continue

                    # Ulanish (internet) holatini tekshirish - yo'q bo'lsa kutish
                    connected = await self._wait_for_connection(user_id)
                    if not connected or not self.is_campaign_active:
                        break

                    now = time.time()
                    flood_wait_until = state.get('flood_wait_until', 0)
                    current_interval = state.get('current_interval', state.get('user_interval', 20))

                    # ✅ TO'G'RI FLOOD WAIT TEKSHIRISH
                    if flood_wait_until > now:
                        wait_time = flood_wait_until - now
                        print(f"  ⏳ Guruh {group_id} FLOOD WAIT - {int(wait_time)}s kutish...")
                        # ✅ BUTUN FLOOD WAIT VAQTINI KUTISH
                        await asyncio.sleep(wait_time)
                        # ✅ FLOOD WAIT TUGAGACH, STATE YANGILASH
                        state['flood_wait_until'] = 0
                        print(f"  ✅ Guruh {group_id} FLOOD WAIT TUGADI")
                        continue

                    success = await self._send_to_group(user_id, campaign_id, group_id, message_text, state)
                    if success:
                        send_count += 1
                        print(f"  ✅ Guruh {group_id} {send_count}-marta yuborildi")

                    # Keyingi yuborish uchun shu guruhning o'z intervalini kutish
                    await asyncio.sleep(state.get('current_interval', current_interval))

                except asyncio.CancelledError:
                    print(f"⏹ Guruh {group_id} bekor qilindi")
                    break
                except Exception as e:
                    print(f"❌ Guruh {group_id} ichki xatolik: {e}")
                    await asyncio.sleep(2)
            
            print(f"🏁 Guruh {group_id} jarayoni tugadi. Jami {send_count} marta yuborildi")
            
        except Exception as e:
            print(f"❌ Guruh {group_id} asosiy xatolik: {e}")
    
    async def start_campaign(self, user_id: int, campaign_id: int, session_string: str, user_interval: int):
        """Kampaniya boshlash - DOIMIY SIKL (CHEKSIZ)"""
        is_valid = await self._check_session_validity(user_id, session_string)
        if not is_valid:
            if self.bot:
                try:
                    await self.bot.send_message(
                        user_id,
                        "❌ *Session bekor qilingan!*\n\n"
                        "Iltimos, '📵 Telegram akkauntni uzish' tugmasini bosib, qayta login qiling."
                    )
                except Exception:
                    pass
            return
        
        self.is_campaign_active = True

        from database import db
        campaign = await db.get_campaign_by_id(campaign_id)
        
        if not campaign:
            print(f"❌ Kampaniya {campaign_id} topilmadi")
            return
        
        message_text = campaign['message_text']
        group_ids = campaign['group_ids']
        
        print(f"🚀 DOIMIY KAMPANIYA {campaign_id} boshlandi (CHEKSIZ)")
        print(f"📝 Xabar: {message_text[:50]}...")
        print(f"📋 Guruhlar soni: {len(group_ids)}")
        print(f"⏰ Interval: {user_interval} sekund")

        # ✅ ENTITY KESHINI YANGILASH
        # Guruh ID'lari bazada oddiy raqam (BIGINT) sifatida saqlanadi. Telethon
        # esa bunday "yalang'och" ID'ni to'g'ri guruhga bog'lash uchun xotiradagi
        # keshga tayanadi (access_hash). Bu kesh client qayta ulanganda
        # (masalan bot qayta ishga tushganda) BO'SHAB QOLADI, va shu sabab
        # avvaldan topilgan guruhlar "topilmadi" xatosini berishi mumkin edi.
        # Shu sabab kampaniya boshida guruh ro'yxatini (dialoglarni) qayta
        # o'qib, keshni yangilab olamiz - user a'zo bo'lgan har bir guruh
        # shu ro'yxatda bo'lgani uchun keshga to'g'ri qayta yoziladi.
        try:
            await self.client.get_dialogs()
        except Exception as e:
            print(f"⚠️ Dialoglarni yangilashda xatolik: {e}")

        # Guruh nomlarini olish
        group_names = {}
        for group_id in group_ids:
            try:
                entity = await self.client.get_entity(group_id)
                group_names[group_id] = getattr(entity, 'title', f'Guruh {group_id}')
            except Exception:
                group_names[group_id] = f'Guruh {group_id}'
        
        for group_id in group_ids:
            self.group_states[group_id] = {
                'user_interval': user_interval,
                'last_sent': 0,
                'current_interval': user_interval,
                'flood_wait_until': 0,
                'has_error': False,
                'is_completed': False,
                'group_name': group_names.get(group_id, f'Guruh {group_id}')
            }
        
        # Userga boshlash haqida xabar
        try:
            if self.bot:
                await self.bot.send_message(
                    user_id,
                    f"🚀 *DOIMIY KAMPANIYA BOSHLANDI!*\n\n"
                    f"📊 Guruhlar: {len(group_ids)} ta\n"
                    f"⏰ Interval: {user_interval} sekund\n"
                    f"⏳ Davomiylik: *CHEKSIZ*\n\n"
                    f"🔄 Xabarlar avtomatik ravishda takrorlanadi...\n"
                    f"⏬ Bloklangan guruhlar avtomatik o'chiriladi\n\n"
                    f"⏹ To'xtatish uchun '🔄 Kampaniyani to'xtatish' tugmasini bosing",
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"⚠️ Xabar yuborishda xatolik: {e}")
        
        # BARCHA GURUHLARNI PARALLEL ISHGA TUSHIRISH
        # Har biri bir zumda emas, ozgina (stagger_gap) farq bilan boshlanadi -
        # shunda kampaniya boshida barcha guruhga bir vaqtda portlab xabar
        # ketmaydi, lekin baribir tez orada hammasi ishga tushadi.
        stagger_gap = min(2.0, user_interval / max(len(group_ids), 1))

        tasks = []
        for idx, group_id in enumerate(group_ids):
            task = asyncio.create_task(
                self._process_single_group(user_id, campaign_id, group_id, message_text, start_delay=idx * stagger_gap)
            )
            self.group_tasks[group_id] = task
            tasks.append(task)
        
        # Barcha tasklar tugashini kutish
        if tasks:
            # Har bir task mustaqil, bittasi xato bo'lsa ham boshqalari davom etadi
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Kampaniya tugagach statistika
        total_groups = len(group_ids)
        successful_groups = sum(1 for s in self.group_states.values() if not s.get('has_error'))
        failed_groups = sum(1 for s in self.group_states.values() if s.get('has_error'))
        
        print(f"⏹ DOIMIY KAMPANIYA {campaign_id} tugadi (user_id: {user_id})")
        print(f"📊 Natija: {successful_groups} ta guruh faol, {failed_groups} ta guruh bloklangan")
        
        # Userga umumiy natija xabari
        if self.bot:
            try:
                if failed_groups == total_groups and total_groups > 0:
                    blocked_groups = "\n".join([
                        f"❌ {s['group_name']}" 
                        for s in self.group_states.values() 
                        if s.get('has_error')
                    ][:10])
                    
                    if failed_groups > 10:
                        blocked_groups += f"\n\n... va yana {failed_groups - 10} ta guruh"
                    
                    await self.bot.send_message(
                        user_id,
                        f"⚠️ *Kampaniya tugadi!*\n\n"
                        f"❌ Barcha guruhlar bloklangan.\n\n"
                        f"📋 *Bloklangan guruhlar:*\n{blocked_groups}\n\n"
                        f"💡 *Tavsiya:*\n"
                        f"1. Guruh adminlaridan yozish huquqini so'rang\n"
                        f"2. Yoki boshqa guruhlarga qo'shiling\n"
                        f"3. 'Xabar' jildini yangilang",
                        parse_mode="Markdown"
                    )
                
                elif failed_groups > 0 and successful_groups > 0:
                    blocked_groups_text = ""
                    if failed_groups <= 5:
                        blocked_groups_text = "\n\n📋 *Bloklangan guruhlar:*\n" + "\n".join([
                            f"❌ {s['group_name']}" 
                            for s in self.group_states.values() 
                            if s.get('has_error')
                        ])
                    
                    await self.bot.send_message(
                        user_id,
                        f"✅ *Kampaniya tugadi!*\n\n"
                        f"📊 *Natija:*\n"
                        f"✅ Faol guruhlar: {successful_groups} ta\n"
                        f"❌ Bloklangan: {failed_groups} ta\n"
                        f"📈 Umumiy: {total_groups} ta guruh{blocked_groups_text}\n\n"
                        f"💡 Bloklangan guruhlarda yozish huquqi yo'q yoki admin tomonidan cheklov qo'yilgan.",
                        parse_mode="Markdown"
                    )
                
                elif successful_groups == total_groups and total_groups > 0:
                    await self.bot.send_message(
                        user_id,
                        f"🎉 *Kampaniya muvaffaqiyatli tugadi!*\n\n"
                        f"✅ Barcha {total_groups} ta guruh faol!\n\n"
                        f"📤 Sizning xabaringiz barcha guruhlarga yetkazildi.",
                        parse_mode="Markdown"
                    )
                
            except Exception as e:
                print(f"⚠️ Statistika xabarini yuborishda xatolik: {e}")
        
        self.is_campaign_active = False
    
    async def stop_campaign(self, user_id: int):
        """Kampaniyani to'xtatish"""
        self.is_campaign_active = False
        
        for group_id, task in self.group_tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.group_tasks.clear()
        self.group_states.clear()

        print(f"⏹ Kampaniya to'xtatildi (user_id: {user_id})")
        
        try:
            if self.bot:
                await self.bot.send_message(
                    user_id,
                    "⏹ *Xabar yuborish to'xtatildi!*\n\n"
                    "Qayta boshlash uchun '📤 Xabar yuborish' tugmasini bosing.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"❌ To'xtatish xabarini yuborishda xatolik: {e}")