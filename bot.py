import asyncio
import os # Новий імпорт для роботи зі змінними середовища
from aiohttp import web # Новий імпорт для вбудованого веб-сервера

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

# --- Конфігурація бота ---
API_TOKEN = '7588127606:AAGscvK5SeIdZ3Qsx_oNzR4cK0A6njFD9mM'
# !!! ОБОВ'ЯЗКОВО ЗАМІНІТЬ ЦЕ НА ВАШ ЧИСЛОВИЙ TELEGRAM ID !!!
YOUR_TELEGRAM_CHAT_ID = 1234567890 # Наприклад: 1234567890

# --- Конфігурація Webhook ---
WEBHOOK_PATH = "/webhook" # Шлях, за яким бот буде приймати оновлення
# !!! ОБОВ'ЯЗКОВО ЗГЕНЕРУЙТЕ ТА ВСТАНОВІТЬ ЦЕ ЯК ЗМІННУ СЕРЕДОВИЩА НА RENDER !!!
# Це секретний токен для перевірки, що запит прийшов від Telegram, а не від когось іншого.
# В коді ми отримуємо його з змінної середовища WEBHOOK_SECRET.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Render автоматично надає ім'я хоста вашого розгорнутого сервісу через цю змінну середовища.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

# Перевірка, чи встановлені необхідні змінні середовища
if not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET environment variable is not set! Please define it on Render.")
if not RENDER_EXTERNAL_HOSTNAME:
    # Ця гілка має активуватися лише під час локального тестування без Render env vars.
    # Для розгортання на Render RENDER_EXTERNAL_HOSTNAME ОБОВ'ЯЗКОВО має бути встановлений.
    raise RuntimeError("RENDER_EXTERNAL_HOSTNAME environment variable is not set. This bot is configured for Render deployment.")

# Формуємо повний URL для вебхука. Render надає HTTPS.
WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}{WEBHOOK_PATH}"

# Список психологів з гіперпосиланнями (залишається без змін)
PSYCHOLOGISTS = {
    "Ткаченко Юлія Леонідівна": "https://doc.ua/ua/doctor/kiev/22001-yuliya-tkachenko/about",
    "Ольга Сергієнко": "https://k-s.org.ua/branches/team/olga-sergiyenko/",
    "Шкварок Наталія Борисівна": "https://uccbt.com.ua/specialists/shkvarok-nataliya-borysivna/",
}

# Ініціалізація бота та диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Створення станів для FSM (Finite State Machine) - залишається без змін ---
class CourseStates(StatesGroup):
    waiting_for_start_confirmation = State()
    waiting_for_psychologist_choice = State()
    waiting_for_custom_psychologist = State()
    waiting_for_final_confirmation = State()

# --- Обробники повідомлень та колбеків - залишаються без змін ---

@dp.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Готова розпочати курс")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Привіт! У мене для тебе сюрприз – 5 сеансів з психологом. Якщо ти готова розпочати, натисни кнопку нижче.",
        reply_markup=keyboard
    )
    await state.set_state(CourseStates.waiting_for_start_confirmation)

@dp.message(CourseStates.waiting_for_start_confirmation, F.text == "Готова розпочати курс")
async def process_start_confirmation(message: Message, state: FSMContext):
    keyboard_builder = types.InlineKeyboardBuilder()
    for name, url in PSYCHOLOGISTS.items():
        keyboard_builder.row(types.InlineKeyboardButton(text=name, url=url, callback_data=f"select_psy_{name}"))
    keyboard_builder.row(types.InlineKeyboardButton(text="Мій варіант", callback_data="select_psy_custom"))

    await message.answer(
        "Чудово! Будь ласка, обери одного з психологів або вкажи свій варіант:",
        reply_markup=keyboard_builder.as_markup()
    )
    await state.set_state(CourseStates.waiting_for_psychologist_choice)

@dp.callback_query(F.data.startswith("select_psy_"), CourseStates.waiting_for_psychologist_choice)
async def process_psychologist_selection(callback_query: types.CallbackQuery, state: FSMContext):
    selected_option = callback_query.data.replace("select_psy_", "")

    if selected_option == "custom":
        await callback_query.message.edit_text("Будь ласка, введи ім'я та посилання на твого психолога (наприклад: 'Ім'я Психолога - Посилання').")
        await state.set_state(CourseStates.waiting_for_custom_psychologist)
    else:
        await state.update_data(chosen_psychologist=selected_option)
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Так, підтверджую", callback_data="confirm_choice")],
                [types.InlineKeyboardButton(text="Змінити вибір", callback_data="change_choice")]
            ]
        )
        await callback_query.message.edit_text(
            f"Ти обрала <b>{selected_option}</b>. Все вірно?",
            reply_markup=keyboard
        )
        await state.set_state(CourseStates.waiting_for_final_confirmation)
    await callback_query.answer()

@dp.message(CourseStates.waiting_for_custom_psychologist)
async def process_custom_psychologist(message: Message, state: FSMContext):
    custom_input = message.text
    if " - " in custom_input and len(custom_input.split(" - ")) == 2:
        name, link = custom_input.split(" - ", 1)
        await state.update_data(chosen_psychologist=f"{name} - {link}")
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Так, підтверджую", callback_data="confirm_choice")],
                [types.InlineKeyboardButton(text="Змінити вибір", callback_data="change_choice")]
            ]
        )
        await message.answer(
            f"Ти обрала <b>{name}</b>. Все вірно?",
            reply_markup=keyboard
        )
        await state.set_state(CourseStates.waiting_for_final_confirmation)
    else:
        await message.answer("Будь ласка, введи ім'я та посилання на твого психолога у форматі: 'Ім'я Психолога - Посилання'.")

@dp.callback_query(F.data == "confirm_choice", CourseStates.waiting_for_final_confirmation)
async def confirm_choice(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    chosen_psychologist = user_data.get("chosen_psychologist")

    if chosen_psychologist in PSYCHOLOGISTS:
        psy_info_for_you = f"Дівчина обрала психолога: <a href='{PSYCHOLOGISTS[chosen_psychologist]}'>{chosen_psychologist}</a>"
    else:
        psy_info_for_you = f"Дівчина обрала свого психолога: {chosen_psychologist}"

    await bot.send_message(chat_id=YOUR_TELEGRAM_CHAT_ID, text=psy_info_for_you, parse_mode=ParseMode.HTML)

    await callback_query.message.edit_text(
        "Дякую за твій вибір! Інформація передана. Очікуй, будь ласка, подальших інструкцій."
    )
    await state.clear()
    await callback_query.answer()

@dp.callback_query(F.data == "change_choice", CourseStates.waiting_for_final_confirmation)
async def change_choice(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard_builder = types.InlineKeyboardBuilder()
    for name, url in PSYCHOLOGISTS.items():
        keyboard_builder.row(types.InlineKeyboardButton(text=name, url=url, callback_data=f"select_psy_{name}"))
    keyboard_builder.row(types.InlineKeyboardButton(text="Мій варіант", callback_data="select_psy_custom"))

    await callback_query.message.edit_text(
        "Гаразд, обери іншого психолога або вкажи свій варіант:",
        reply_markup=keyboard_builder.as_markup()
    )
    await state.set_state(CourseStates.waiting_for_psychologist_choice)
    await callback_query.answer()

# --- Головна функція для запуску бота у режимі Webhook ---
async def main():
    # Render надає змінну середовища PORT, яку ми маємо використовувати.
    # Якщо PORT не встановлено (наприклад, при локальному запуску), використовуємо 8080 за замовчуванням.
    port = int(os.environ.get("PORT", 8080))

    # Встановлюємо webhook URL у Telegram. Це повідомляє Telegram, куди надсилати оновлення.
