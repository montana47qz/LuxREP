import os
import re
import asyncio
from decimal import Decimal, ROUND_UP
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.media_group import MediaGroupBuilder
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
USD_KZT = Decimal(os.getenv("USD_KZT", "470"))
USD_RUB = Decimal(os.getenv("USD_RUB", "92"))

bot = Bot(
    token=TOKEN,
    session=AiohttpSession(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

media_groups = {}

# === ХЕЛПЕРЫ ===
def process_text(text: str) -> str:
    pattern = r"([\d]+(?:[.,]\d+)?)\s?\$"
    match = re.search(pattern, text)

    if not match:
        return text

    original_price_usd = Decimal(match.group(1).replace(",", "."))
    increased = (original_price_usd * Decimal("1.3")).quantize(Decimal("0.5"), rounding=ROUND_UP)

    price_kzt = int(increased * USD_KZT)
    price_rub = int(increased * USD_RUB)

    new_text = re.sub(
        pattern,
        f"<b>{increased} $</b>\n<b>{price_kzt} ₸</b>\n<b>{price_rub} ₽</b>",
        text
    )

    # Заменяем WhatsApp ссылку
    new_text = re.sub(r"wa\.me/\d+", "wa.me/77767616600", new_text)

    return new_text

# === ОБРАБОТКА АЛЬБОМОВ ===
@dp.message(F.media_group_id)
async def handle_album(message: Message):
    media_group_id = message.media_group_id
    if media_group_id not in media_groups:
        media_groups[media_group_id] = []

    media_groups[media_group_id].append(message)

    # Ожидаем поступление всех сообщений в альбоме
    await asyncio.sleep(1)

    if media_group_id not in media_groups:
        return

    messages = media_groups.pop(media_group_id)

    # Объединяем медиа и обрабатываем текст
    builder = MediaGroupBuilder()
    caption = None

    for msg in messages:
        if msg.photo:
            photo = msg.photo[-1]
            if not caption and msg.caption:
                caption = process_text(msg.caption)
            builder.add_photo(media=photo.file_id)

    builder._media[0].caption = caption or ""
    builder._media[0].parse_mode = ParseMode.HTML

    await bot.send_media_group(chat_id=TARGET_CHAT_ID, media=builder.build())

# === ОБЫЧНЫЕ ФОТО ===
@dp.message(F.photo)
async def handle_single_photo(message: Message):
    caption = process_text(message.caption or "")
    await bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=caption, parse_mode=ParseMode.HTML)

# === ТЕКСТ ===
@dp.message(F.text)
async def handle_text(message: Message):
    new_text = process_text(message.text)
    await bot.send_message(chat_id=TARGET_CHAT_ID, text=new_text)

# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
