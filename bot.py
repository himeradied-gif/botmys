import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TOKEN, DAILY_INCOME, SERVICE_DAYS, TIMEZONE, ADMIN_ID
from database import init_db, get_user, add_user, update_checkin, add_earnings, deactivate_user
from keyboards import main_menu, category_keyboard
from utils import apply_penalties_and_update, auto_apply_daily_penalties
from admin import admin_panel, broadcast, is_admin

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

BANNER_PATH = "banners/workk.jpg"   # укажи правильный путь или удали файл


async def send_with_banner(chat_id: int, text: str, reply_markup=None):
    try:
        banner = FSInputFile(BANNER_PATH)
        await bot.send_photo(chat_id, photo=banner, caption=text, reply_markup=reply_markup)
    except Exception:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)


def calculate_remaining(user) -> int:
    activation = datetime.fromisoformat(user["activation_date"]).date()
    today = datetime.now(TIMEZONE).date()
    days_passed = (today - activation).days
    return max(0, SERVICE_DAYS - days_passed)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    user = get_user(user_id)

    if user and user["active"]:
        remaining = calculate_remaining(user)
        text = (f"👋 С возвращением!\n"
                f"Твоя активная услуга: категория {user['category']}\n"
                f"Осталось дней: {remaining}")
        await send_with_banner(user_id, text, reply_markup=main_menu())
    else:
        text = "🌟 Выбери категорию услуги (срок 30 дней):"
        await send_with_banner(user_id, text, reply_markup=category_keyboard())


@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def select_category(callback: CallbackQuery):
    cat_num = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    username = callback.from_user.username or "no_username"

    add_user(user_id, username, cat_num)
    daily = DAILY_INCOME[cat_num]

    text = (f"✅ Ты выбрал категорию {cat_num}\n"
            f"Доход в день: ${daily}\n"
            f"Срок: 30 дней\n\n"
            f"Нажимай «РАБОТАЮ» каждый день до полуночи по Москве!")

    await send_with_banner(user_id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user["active"]:
        await callback.answer("У тебя нет активной услуги. Напиши /start")
        return

    cat = user["category"]
    income = DAILY_INCOME[cat]
    earned = user["total_earned"]
    penalty = user["total_penalty"]
    net = earned - penalty
    remaining = calculate_remaining(user)

    now_msk = datetime.now(TIMEZONE)
    midnight = (now_msk + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    hours_left = max(0, (midnight - now_msk).total_seconds() / 3600)

    text = (f"📊 *Твой профиль*\n\n"
            f"Услуга: категория {cat}\n"
            f"Доход в день: ${income}\n"
            f"Осталось дней: {remaining}\n"
            f"💰 Начислено: ${earned:.2f}\n"
            f"⚠️ Штрафы: ${penalty:.2f}\n"
            f"💵 Чистый доход: ${net:.2f}\n\n"
            f"🕒 Московское время: {now_msk.strftime('%H:%M:%S')}\n"
            f"⏳ До полуночи: {hours_left:.1f} ч.")

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer("parse_mode", "Markdown")


@dp.callback_query(lambda c: c.data == "my_service")
async def my_service(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user["active"]:
        await callback.answer("Нет активной услуги")
        return

    text = (f"📟 Твоя услуга: категория {user['category']}\n"
            f"Доход в день: ${DAILY_INCOME[user['category']]}\n"
            f"Осталось дней: {calculate_remaining(user)}")

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "work_today")
async def work_today(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not user or not user["active"]:
        await callback.answer("У тебя нет активной услуги. Напиши /start", show_alert=True)
        return

    await apply_penalties_and_update(user_id)

    user = get_user(user_id)  # обновляем данные после штрафов
    if not user or not user["active"]:
        await callback.answer("Срок услуги истёк. Начни новую через /start", show_alert=True)
        return

    last_date = datetime.fromisoformat(user["last_checkin"]).date()
    today = datetime.now(TIMEZONE).date()

    if last_date == today:
        await callback.answer("Ты уже сегодня отметился!", show_alert=True)
        return

    if calculate_remaining(user) <= 0:
        deactivate_user(user_id)
        await callback.answer("Срок услуги истёк.", show_alert=True)
        return

    # Начисляем доход
    income = DAILY_INCOME[user["category"]]
    add_earnings(user_id, income)
    update_checkin(user_id, datetime.now(TIMEZONE).isoformat())

    remaining = calculate_remaining(user) - 1

    if remaining <= 0:
        deactivate_user(user_id)
        text = f"✅ Получено ${income} за сегодня.\n\n🎉 Твой 30-дневный период завершён!"
    else:
        text = f"✅ Получено ${income} за сегодня.\nОсталось дней: {remaining}"

    await send_with_banner(user_id, text, reply_markup=main_menu())
    await callback.answer()


@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    await admin_panel(message)


@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    await broadcast(message, bot)


async def main():
    init_db()
    scheduler.add_job(auto_apply_daily_penalties, CronTrigger(hour=0, minute=0, timezone=TIMEZONE))
    scheduler.start()

    print("Бот успешно запущен. Планировщик активен (00:00 по Москве)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
