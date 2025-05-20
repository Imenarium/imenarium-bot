import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, Text  # Проверяем стандартный импорт
import asyncio
import pandas as pd
import random
from datetime import datetime, timedelta
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка сценария из Excel
try:
    df = pd.read_excel("scenario.xlsx")
except Exception as e:
    logger.error(f"Не удалось загрузить scenario.xlsx: {e}")
    raise

# Инициализация бота
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")  # Используем переменную окружения
bot = Bot(token=API_TOKEN)
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

# Расчет даты +8 дней
def get_date_plus_8():
    return (datetime.now() + timedelta(days=8)).strftime("%d.%m.%Y")

# Случайные ответы
fallback_responses = [
    "{имя}, боюсь, я не понимаю человеческих слов...\nНо если вы нажмёте одну из кнопок ниже — я точно вас услышу! ✨",
    "{имя}, возможно, вы сказали что-то важное...\nНо, увы, я понимаю только кнопочки 😅\nДавайте выберем что-нибудь вместе?",
    "{имя}, кажется, вы отправили звёздное послание без кнопки!\nЯ, к сожалению, не телепат. Но кнопки — моя суперсила 🚀",
    "{имя}, вы невероятны!\nНо я — не маг, не волшебник, а всего лишь бот...\nИ мне очень помогают кнопки 👇"
]

# Словарь блоков
blocks = {row['Блок']: row for _, row in df.iterrows()}

# Карта ключевых слов
keyword_map = {}
for _, row in df.iterrows():
    if pd.notna(row['Ключевые слова']):
        keys = [k.strip().lower() for k in str(row['Ключевые слова']).split(';')]
        for k in keys:
            keyword_map[k] = row['Блок']

# Обработка команды /start
@dp.message(Command(commands=["start"]))
async def start_command(message: Message):
    await send_block(message, "Приветствие")

# Обработка текстовых сообщений
@dp.message(Text)
async def handle_message(message: Message):
    user_input = message.text.strip()
    user_name = message.from_user.first_name or "друг"

    # Проверка ключевых слов
    lower_text = user_input.lower()
    for key, target_block in keyword_map.items():
        if key in lower_text:
            await send_block(message, target_block)
            return

    # Проверка совпадений с кнопками
    for block_name, row in blocks.items():
        if pd.notna(row['Кнопки']):
            buttons = [b.strip() for b in str(row['Кнопки']).split('|')]
            transitions = [t.strip().lstrip('→').strip() for t in str(row['Переходы']).split('|')]
            if len(buttons) != len(transitions):
                logger.error(f"Несоответствие кнопок и переходов в блоке {block_name}")
                continue
            button_map = dict(zip(buttons, transitions))
            if user_input in button_map:
                await send_block(message, button_map[user_input])
                return

    # Случайный ответ
    text = random.choice(fallback_responses).replace("{имя}", user_name)
    await message.answer(text)

# Отправка содержимого блока
async def send_block(message: Message, block_name: str):
    if block_name not in blocks:
        await message.answer("Блок не найден.")
        return

    row = blocks[block_name]
    user_name = message.from_user.first_name or "друг"

    try:
        # Обработка блока "Видео"
        if block_name.lower() == "видео":
            media_files = str(row['Медиа']).split(';') if pd.notna(row['Медиа']) else []
            captions = str(row['Текст сообщения']).split(';') if pd.notna(row['Текст сообщения']) else []
            for i, file in enumerate(media_files):
                file = file.strip()
                caption = captions[i].strip() if i < len(captions) else ""
                if os.path.exists(file):
                    try:
                        await message.answer_video(video=open(file, 'rb'), caption=caption)
                    except Exception as e:
                        logger.error(f"Не удалось отправить видео {file}: {e}")
                        await message.answer(f"Ошибка при отправке видео: {file}")
                else:
                    logger.error(f"Видео не найдено: {file}")
                    await message.answer(f"Файл не найден: {file}")
            return

        # Обработка медиа (фото)
        if pd.notna(row['Медиа']):
            media_files = str(row['Медиа']).split(';')
            for file in media_files:
                file = file.strip()
                if os.path.exists(file):
                    try:
                        await message.answer_photo(photo=open(file, 'rb'))
                    except Exception as e:
                        logger.error(f"Не удалось отправить фото {file}: {e}")
                        await message.answer(f"Ошибка при отправке изображения: {file}")
                else:
                    logger.error(f"Фото не найдено: {file}")
                    await message.answer(f"Файл не найден: {file}")

        # Обработка текста
        if pd.notna(row['Текст сообщения']):
            text = row['Текст сообщения']
            text = text.replace("{приветствие}", get_greeting())
            text = text.replace("{имя}", user_name)
            text = text.replace("{дата+8}", get_date_plus_8())
            await message.answer(text)

        # Обработка кнопок
        if pd.notna(row['Кнопки']) and pd.notna(row['Переходы']):
            buttons = [b.strip() for b in str(row['Кнопки']).split('|')]
            transitions = [t.strip().lstrip('→').strip() for t in str(row['Переходы']).split('|')]
            if len(buttons) != len(transitions):
                logger.error(f"Несоответствие кнопок и переходов в блоке {block_name}")
                await message.answer("Ошибка в конфигурации кнопок.")
                return

            reply_buttons = []
            inline_buttons = []
            for btn_text, transition in zip(buttons, transitions):
                if transition.startswith("http") or transition.startswith("tel:") or transition.startswith("mailto:"):
                    inline_buttons.append([InlineKeyboardButton(text=btn_text, url=transition)])
                else:
                    reply_buttons.append(KeyboardButton(text=btn_text))

            # Отправка reply-клавиатуры
            if reply_buttons:
                markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(*reply_buttons)
                await message.answer("Выберите действие:", reply_markup=markup)

            # Отправка inline-клавиатуры
            if inline_buttons:
                inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
                await message.answer("Дополнительные действия:", reply_markup=inline_markup)

    except Exception as e:
        logger.error(f"Ошибка в send_block для {block_name}: {e}")
        await message.answer("Произошла ошибка при обработке блока.")

# Основная функция
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске поллинга: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())