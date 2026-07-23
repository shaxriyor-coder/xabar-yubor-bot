"""Kichik yordamchi funksiyalar - hech qaysi bo'limga tegishli bo'lmagan umumiy narsalar."""

from io import BytesIO

import qrcode
from aiogram.types import BufferedInputFile


# "Xabar yuborish" jarayonining har bir bosqichida ko'rsatiladigan qisqa eslatma
INTERNET_REMINDER = (
    "\n\n📡 Eslatma: xabar yuborish jarayoni davomida internet aloqangiz "
    "barqaror va doimiy ulangan bo'lishi shart."
)


def make_qr_image(url: str) -> BufferedInputFile:
    """QR-login havolasidan Telegramga yuborsa bo'ladigan rasm (PNG) yaratish"""
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename="qr_login.png")
