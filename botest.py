

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка базы данных SQLite
DATABASE_URL = "sqlite:///messages.db"
engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()

# Определение модели таблицы
class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    message_text = Column(Text, nullable=False)

# Создание таблицы в базе данных
Base.metadata.create_all(engine)

# Создание сессии для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()

# Настройка бота
# API_TOKEN = 'eMEiNrjpkpY'  # Замените на ваш токен
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Создание клавиатуры с кнопкой "CHECK"
def get_check_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="CHECK"))
    return builder.as_markup(resize_keyboard=True)

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Нажмите кнопку 'CHECK', чтобы сохранить сообщение в базу данных.",
        reply_markup=get_check_keyboard()
    )

# Обработчик кнопки "CHECK"
@dp.message(lambda message: message.text == "CHECK")
async def process_check_button(message: types.Message):
    # Получаем текст сообщения
    text_to_save = message.text

    # Сохраняем текст в базу данных
    new_message = Message(message_text=text_to_save)
    session.add(new_message)
    session.commit()

    # Отправляем подтверждение пользователю
    # await message.answer(f"Сообщение '{text_to_save}' сохранено в базу данных.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


