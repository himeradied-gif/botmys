from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    buttons = [
        [InlineKeyboardButton(text="📋 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="✅ РАБОТАЮ", callback_data="work_today")],
        [InlineKeyboardButton(text="ℹ️ Моя услуга", callback_data="my_service")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def category_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1️⃣ Электросамокаты / велосипеды (3.4$/день)", callback_data="cat_1")],
        [InlineKeyboardButton(text="2️⃣ Повербанки в аренду (2$/день)", callback_data="cat_2")],
        [InlineKeyboardButton(text="3️⃣ Крипто-майнинг фермы (4$/день)", callback_data="cat_3")],
        [InlineKeyboardButton(text="4️⃣ Недвижимость посуточно (2.8$/день)", callback_data="cat_4")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
