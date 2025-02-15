import re
import logging
from datetime import datetime
import pytz  # Импортируем библиотеку для работы с часовыми поясами
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

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
    user_id = Column(Integer, nullable=False)  # ID пользователя
    username = Column(String(100), nullable=True)  # Имя пользователя
    message_text = Column(Text, nullable=False)  # Текст сообщения
    date = Column(DateTime, nullable=False)  # Дата и время
    url_m3u8 = Column(String(255), nullable=True)  # URL M3U8
    name = Column(String(100), nullable=True)  # Имя URL
    promt = Column(String(255), nullable=True)  # Промт


# Создание таблицы в базе данных
Base.metadata.create_all(engine)

# Создание сессии для работы с базой данных
Session = sessionmaker(bind=engine)
session = Session()

# Настройка бота
API_TOKEN = '7650957440:AAEDT9Ru9J69LmQTN9TgSiineMEiNrjpkpY'  # Замените на ваш токен
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# Определение состояний FSM
class Form(StatesGroup):
    url_m3u8 = State()  # Состояние для ввода URL M3U8
    name = State()  # Состояние для ввода имени URL


# Установка часового пояса (Киев)
kiev_tz = pytz.timezone('Europe/Kiev')


# Создание клавиатуры
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="CHECK"))
    builder.add(KeyboardButton(text="Список URL"))
    builder.add(KeyboardButton(text="ONLINE-TV"))
    return builder.as_markup(resize_keyboard=True)


# Функция для проверки URL
def is_valid_url(url: str) -> bool:
    """
    Проверяет, начинается ли URL на "http" и заканчивается ли на "m3u8".
    """
    pattern = re.compile(r'^https?://.*\.m3u8$')  # Регулярное выражение для проверки
    return bool(pattern.match(url))


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать! Используйте кнопки для управления.",
        reply_markup=get_main_keyboard()
    )


# Обработчик кнопки "CHECK"
@dp.message(lambda message: message.text == "CHECK")


async def process_check_button(message: types.Message, state: FSMContext):
    # Запрашиваем URL M3U8
    await message.answer("Пожалуйста, введите URL M3U8 (должен начинаться на 'http' и заканчиваться на 'm3u8'):")
    # Устанавливаем состояние для ожидания ввода URL M3U8
    await state.set_state(Form.url_m3u8)


# Обработчик для ввода URL M3U8
@dp.message(Form.url_m3u8)
async def process_url_m3u8(message: types.Message, state: FSMContext):
    url_m3u8 = message.text  # URL M3U8, введенный пользователем
    # # Сбрасываем состояние
    # await state.clear()

    # Проверяем URL
    if not is_valid_url(url_m3u8):
        await message.answer(
            "Некорректный URL. Пожалуйста, введите URL, который начинается на 'http' и заканчивается на 'm3u8'.")
        return  # Не сбрасываем состояние, чтобы пользователь мог ввести URL заново

    # Проверяем, существует ли URL уже в базе данных
    existing_url = session.query(Message).filter(Message.url_m3u8 == url_m3u8).first()
    if existing_url:
        await message.answer("Этот URL уже существует в списке.")
        await state.clear()
        return

    # Сохраняем URL в состояние
    await state.update_data(url_m3u8=url_m3u8)

    # Запрашиваем имя для URL
    await message.answer("Пожалуйста, введите имя для этого URL:")
    await state.set_state(Form.name)


# Обработчик для ввода имени URL
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text  # Имя, введенное пользователем
    data = await state.get_data()  # Получаем сохраненный URL
    url_m3u8 = data.get("url_m3u8")

    # Собираем данные
    user_id = message.from_user.id
    username = message.from_user.username
    message_text = "CHECK"  # Текст кнопки
    date = datetime.now(kiev_tz)  # Устанавливаем время в часовом поясе Киев
    promt = "Ввод пользователя"  # Пример промта (можно заменить на ввод от пользователя)

    try:
        # Сохраняем данные в базу данных
        new_message = Message(
            user_id=user_id,
            username=username,
            message_text=message_text,
            date=date,
            url_m3u8=url_m3u8,
            name=name,
            promt=promt
        )
        session.add(new_message)
        session.commit()

        # Логируем успешное сохранение
        logger.info(f"Данные сохранены в базу данных: {new_message}")

        # Отправляем подтверждение пользователю
        green_circle = '\U0001F7E2'
        await message.answer(
            f"{green_circle} Данные успешно сохранены:\n"
            f"ID: {new_message.id}\n"
            f"User ID: {new_message.user_id}\n"
            f"Username: {new_message.username}\n"
            f"Текст сообщения: {new_message.message_text}\n"
            f"Дата: {new_message.date}\n"
            f"URL M3U8: {new_message.url_m3u8}\n"
            f"Имя: {new_message.name}\n"
            f"Промт: {new_message.promt}"
        )
    except SQLAlchemyError as e:
        # Логируем ошибку
        logger.error(f"Ошибка при сохранении данных в базу данных: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
    finally:
        # Сбрасываем состояние
        await state.clear()


# Обработчик кнопки "Список URL"
@dp.message(lambda message: message.text == "Список URL")
async def process_list_urls(message: types.Message, state: FSMContext):
    # Сбрасываем состояние, если оно было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    # Получаем все URL из базы данных
    urls = session.query(Message).all()

    if not urls:
        await message.answer("Список URL пуст.")
        return

    # Формируем текстовый список URL с порядковыми номерами и именами
    url_list = "\n".join(
        [f"{i + 1}. {url.name} - {url.url_m3u8} ({url.date.astimezone(kiev_tz).strftime('%Y-%m-%d %H:%M:%S')})" for
         i, url in enumerate(urls)])

    # Формируем inline-кнопки для удаления и просмотра
    builder = InlineKeyboardBuilder()
    for i, url in enumerate(urls):
        # Добавляем кнопки "Del" и "View" для каждого URL в одну строку
        builder.row(
            InlineKeyboardButton(text=f"Del {i + 1}", callback_data=f"delete_{url.id}"),
            InlineKeyboardButton(text=f"View {i + 1}", callback_data=f"watch_{url.id}")
        )

    # Отправляем сообщение с нумерованным списком URL и кнопками
    await message.answer(
        f"Список URL:\n{url_list}",
        reply_markup=builder.as_markup()
    )


# Обработчик для удаления URL через inline-кнопку
@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def process_delete_url(callback: types.CallbackQuery):
    url_id = int(callback.data.split("_")[1])  # Получаем ID URL из callback_data
    url = session.query(Message).filter(Message.id == url_id).first()

    if url:
        session.delete(url)
        session.commit()
        await callback.message.answer(f"URL с ID {url_id} успешно удален.")
    else:
        await callback.message.answer(f"URL с ID {url_id} не найден.")

    # Обновляем список URL
    await process_list_urls(callback.message)


# Обработчик для просмотра URL через inline-кнопку
@dp.callback_query(lambda c: c.data.startswith("watch_"))
async def process_watch_url(callback: types.CallbackQuery):
    # Получаем ID URL из callback_data
    url_id = int(callback.data.split("_")[1])

    # Ищем URL в базе данных
    url = session.query(Message).filter(Message.id == url_id).first()

    if url:
        # Отправляем пользователю ссылку для просмотра
        await callback.message.answer(f"Смотрите ONLINE-TV: {url.url_m3u8}")
    else:
        # Если URL не найден, отправляем сообщение об ошибке
        await callback.message.answer("URL не найден.")


# Обработчик кнопки "ONLINE-TV"
@dp.message(lambda message: message.text == "ONLINE-TV")


async def process_online_tv(message: types.Message, state: FSMContext):
    # Сбрасываем состояние, если оно было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()  # Сбрасываем состояние

    # Получаем последний добавленный URL
    last_url = session.query(Message).order_by(Message.id.desc()).first()

    if not last_url:
        await message.answer("Нет доступных URL для просмотра.")
        return

    # Отправляем ссылку для просмотра
    await message.answer(f"Смотрите ONLINE-TV: {last_url.url_m3u8}")


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())