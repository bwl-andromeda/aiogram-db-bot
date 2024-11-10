from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


async def start_kb():
    kb_list = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="💰 Пополнение"), KeyboardButton(text="💸 Трата")],
        [KeyboardButton(text="📂 Категории")],
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True
    )
    return keyboard
