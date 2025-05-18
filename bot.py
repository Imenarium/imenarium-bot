
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from aiogram import F
import asyncio
import pandas as pd
import random
from datetime import datetime

# Загрузка сценария из Excel
df = pd.read_excel("scenario.xlsx")

# Инициализация
API_TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Приветствия по времени суток
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 24:
        return "Добрый вечер"
    else:
        return "Доброй ночи"

# Случайные ответы на произвольные сообщения
fallback_responses = [
    "{имя}, боюсь, я не понимаю человеческих слов...\nНо если вы нажмёте одну из кнопок ниже — я точно вас услышу! ✨",
    "{имя}, возможно, вы сказали что-то важное...\nНо, увы, я понимаю только кнопочки 😅\nДавайте выберем что-нибудь вместе?",
    "{имя}, кажется, вы отправили звёздное послание без кнопки!\nЯ, к сожалению, не телепат. Но кнопки — моя суперсила 🚀",
    "{имя}, вы невероятны!\nНо я — не маг, не волшебник, а всего лишь бот...\nИ мне очень помогают кнопки 👇"
]

# Словарь блоков
blocks = {row['Блок']: row for _, row in df.iterrows()}

# Ключевые слова
keyword_map = {}
for _, row in df.iterrows():
    if pd.notna(row['Ключевые слова']):
        keys = [k.strip().lower() for k in str(row['Ключевые слова']).split(';')]
        for k in keys:
            keyword_map[k] = row['Блок']

# Обработка кнопок
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_input = message.text.strip()
    user_name = message.from_user.first_name or "друг"

    # 1. Проверка на ключевое слово
    lower_text = user_input.lower()
    for key, target_block in keyword_map.items():
        if key in lower_text:
            await send_block(message, target_block)
            return

    # 2. Проверка на совпадение с кнопкой
    for block_name, row in blocks.items():
        if pd.notna(row['Кнопки']):
            buttons = [b.strip() for b in str(row['Кнопки']).split('|')]
            transitions = [t.strip().lstrip('→').strip() for t in str(row['Переходы']).split('|')]
            button_map = dict(zip(buttons, transitions))
            if user_input in button_map:
                await send_block(message, button_map[user_input])
                return

    # 3. Иначе — случайный fallback-ответ
    text = random.choice(fallback_responses).replace("{имя}", user_name)
    await message.answer(text)

# Отправка блока по имени
async def send_block(message: types.Message, block_name: str):
    if block_name not in blocks:
        await message.answer("Блок не найден.")
        return

    row = blocks[block_name]

    # Особая логика для блока 'Видео'
    if block_name.lower() == "видео":
        media_files = str(row['Медиа']).split(';')
        captions = str(row['Текст сообщения']).split(';')
        for file, caption in zip(media_files, captions):
            await message.answer_video(open(file.strip(), 'rb'), caption=caption.strip())
    else:
        # Отправка медиа (если есть)
        if pd.notna(row['Медиа']):
            media_files = str(row['Медиа']).split(';')
            for file in media_files:
                await message.answer_photo(open(file.strip(), 'rb'))

        # Текст
        if pd.notna(row['Текст сообщения']):
            text = row['Текст сообщения']
            text = text.replace("{приветствие}", get_greeting())
            text = text.replace("{имя}", message.from_user.first_name or "друг")
                text = text.replace("{дата+8}", get_date_plus_8())
            await message.answer(text)

    # Кнопки
    if pd.notna(row['Кнопки']) and pd.notna(row['Переходы']):
        buttons = [b.strip() for b in str(row['Кнопки']).split('|')]
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*[KeyboardButton(text=b) for b in buttons])
        await message.answer("Выберите действие:", reply_markup=markup)

# Запуск
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
