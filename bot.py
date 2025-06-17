import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- Конфігурація бота ---
API_TOKEN = '7588127606:AAGscvK5SeIdZ3Qsx_oNzR4cK0A6njFD9mM'
YOUR_TELEGRAM_CHAT_ID = 680454116 # Ваш числовий Telegram ID

# Список психологів з гіперпосиланнями
PSYCHOLOGISTS = {
    "Ткаченко Юлія Леонідівна": "https://doc.ua/ua/doctor/kiev/22001-yuliya-tkachenko/about",
    "Ольга Сергієнко": "https://k-s.org.ua/branches/team/olga-sergiyenko/",
    "Шкварок Наталія Борисівна": "https://uccbt.com.ua/specialists/shkvarok-nataliya-borysivna/",
}

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- Створення станів для FSM (Finite State Machine) ---
class CourseStates(StatesGroup):
    waiting_for_start_confirmation = State()
    waiting_for_psychologist_choice = State()
    waiting_for_custom_psychologist = State()
    waiting_for_final_confirmation = State()

# --- Обробник команди /start ---
@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
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

# --- Обробник згоди розпочати курс ---
@dp.message(Text("Готова розпочати курс"), CourseStates.waiting_for_start_confirmation)
async def process_start_confirmation(message: types.Message, state: FSMContext):
    keyboard_builder = types.InlineKeyboardBuilder()
    for name, url in PSYCHOLOGISTS.items():
        keyboard_builder.row(types.InlineKeyboardButton(text=name, url=url, callback_data=f"select_psy_{name}"))
    keyboard_builder.row(types.InlineKeyboardButton(text="Мій варіант", callback_data="select_psy_custom"))

    await message.answer(
        "Чудово! Будь ласка, обери одного з психологів або вкажи свій варіант:",
        reply_markup=keyboard_builder.as_markup()
    )
    await state.set_state(CourseStates.waiting_for_psychologist_choice)

# --- Обробник вибору психолога через inline-кнопки ---
@dp.callback_query(Text(startswith="select_psy_"), CourseStates.waiting_for_psychologist_choice)
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

# --- Обробник введення власного варіанту психолога ---
@dp.message(CourseStates.waiting_for_custom_psychologist)
async def process_custom_psychologist(message: types.Message, state: FSMContext):
    custom_input = message.text
    # Проста валідація, можна додати більш складну
    if " - " in custom_input and len(custom_input.split(" - ")) == 2:
        name, link = custom_input.split(" - ", 1)
        # Додаємо психолога до словника для відображення в майбутньому (опціонально)
        # PSYCHOLOGISTS[name] = link
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

# --- Обробник підтвердження/зміни вибору ---
@dp.callback_query(Text("confirm_choice"), CourseStates.waiting_for_final_confirmation)
async def confirm_choice(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    chosen_psychologist = user_data.get("chosen_psychologist")

    # Формуємо повідомлення для вас
    if chosen_psychologist in PSYCHOLOGISTS:
        psy_info_for_you = f"Дівчина обрала психолога: <a href='{PSYCHOLOGISTS[chosen_psychologist]}'>{chosen_psychologist}</a>"
    else: # Це для "Мого варіанту"
        psy_info_for_you = f"Дівчина обрала свого психолога: {chosen_psychologist}"
    
    # Знаходимо ваш ID за username
    # Цей крок може бути складним без прямого доступу до вашого ID.
    # Найкраще, якщо ви самі першим напишете боту, щоб ваш ID був доступний.
    # Для тестування можна використати message.from_user.id з вашого повідомлення до бота.
    # Замість 'YOUR_TELEGRAM_USERNAME' краще використовувати ваш числовий Telegram ID.
    # Наприклад, якщо ваш ID 123456789, то просто YOUR_CHAT_ID = 123456789
    
    # Тимчасове рішення: якщо YOUR_TELEGRAM_USERNAME відомий, спробуйте надіслати йому.
    # АЛЕ, це не гарантує, що бот зможе знайти чат по username без попередньої взаємодії.
    # НАЙКРАЩЕ РІШЕННЯ: змініть YOUR_TELEGRAM_USERNAME на ваш числовий ID у Telegram.
    # Як дізнатися свій ID: напишіть будь-якому боту @userinfobot або @getmyid_bot
    
    # Припускаємо, що ви вже взаємодіяли з ботом, і ми можемо отримати ваш chat_id.
    # У реальному проекті ви б зберігали chat_id адміністратора десь (наприклад, в конфігурації).
    # Для цього прикладу я просто використовую ваш username як орієнтир,
    # але для надійного надсилання потрібно знати chat_id.

    # Оскільки user id телеграму дано як "andriy_pisotskiy" (username), а не числовий ID,
    # і бот не може просто так надсилати повідомлення за username, якщо не було попередньої
    # взаємодії або якщо username не є частиною збережених чатів,
    # я залишаю це місце з коментарем.
    # Якщо ви хочете, щоб це працювало одразу, вам потрібно змінити YOUR_TELEGRAM_USERNAME
    # на ваш числовий Telegram ID.
    
    # Наприклад, якщо ваш ID 123456789:
    # YOUR_CHAT_ID = 123456789
    # await bot.send_message(chat_id=YOUR_CHAT_ID, text=psy_info_for_you, parse_mode=ParseMode.HTML)
    
    # Для цілей демонстрації та якщо ви не хочете змінювати YOUR_TELEGRAM_USERNAME на ID:
    # Можна спробувати знайти користувача за username, але це ненадійно і не рекомендується
    # для критичного функціоналу. Надійніше - це chat_id.
    # Оскільки бот не може ініціювати розмову з вами за username без попередньої взаємодії,
    # я виведу повідомлення про вибір прямо в консоль або журнал,
    # а в робочому боті ви б тут використали ваш числовий Telegram ID.
    
    # Замість надсилання вам, поки що виведемо в консоль
    await bot.send_message(chat_id=YOUR_TELEGRAM_CHAT_ID, text=psy_info_for_you, parse_mode=ParseMode.HTML)
    
    # Тепер надсилаємо повідомлення дівчині
    await callback_query.message.edit_text(
        "Дякую за твій вибір! Інформація передана. Очікуй, будь ласка, подальших інструкцій."
    )
    await state.clear() # Очищаємо стан після завершення процесу
    await callback_query.answer()

@dp.callback_query(Text("change_choice"), CourseStates.waiting_for_final_confirmation)
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


# --- Запуск бота ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())