import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TOKEN, DAILY_INCOME, PENALTY, SERVICE_DAYS, TIMEZONE, ADMIN_ID
from database import init_db, get_user, add_user, update_checkin, add_earnings, deactivate_user
from keyboards import main_menu, category_keyboard
from utils import apply_penalties_and_update, auto_apply_daily_penalties
from admin import admin_panel, broadcast, is_admin

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

BANNER_PATH = "banners/workk.jpg"


async def send_with_banner(chat_id: int, text: str, reply_markup=None):
    """Отправляет сообщение с баннером. Если баннер не найден — отправляет только текст."""
    try:
        full_path = os.path.join(os.getcwd(), BANNER_PATH)
        
        if os.path.exists(full_path):
            banner = FSInputFile(full_path)
            await bot.send_photo(
                chat_id=chat_id,
                photo=banner,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
            print(f"⚠️ Баннер не найден: {full_path}")
            
    except Exception as e:
        print(f"❌ Ошибка отправки баннера: {e}")
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except:
            pass


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
        text = (
            f"👋 <b>С возвращением!</b>\n\n"
            f"Активная услуга: категория <b>{user['category']}</b>\n"
            f"Осталось дней: <b>{remaining}</b>"
        )
        await send_with_banner(user_id, text, reply_markup=main_menu())
    else:
        text = "🌟 <b>Выбери категорию услуги</b> (срок 30 дней):"
        await send_with_banner(user_id, text, reply_markup=category_keyboard())


@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def select_category(callback: CallbackQuery):
    cat_num = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    username = callback.from_user.username or "no_username"

    add_user(user_id, username, cat_num)
    daily = DAILY_INCOME[cat_num]

    text = (
        f"✅ <b>Услуга активирована!</b>\n\n"
        f"Категория: <b>{cat_num}</b>\n"
        f"Доход в день: <b>${daily}</b>\n"
        f"Срок: <b>30 дней</b>\n\n"
        f"Нажимай кнопку <b>✅ РАБОТАЮ</b> каждый день до 23:59 по Москве!"
    )

    await send_with_banner(user_id, text, reply_markup=main_menu())
    await callback.answer("Услуга успешно активирована!")


@dp.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user["active"]:
        await callback.answer("У тебя нет активной услуги.", show_alert=True)
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

    text = (
        f"📊 <b>Твой профиль</b>\n\n"
        f"Услуга: категория <b>{cat}</b>\n"
        f"Доход в день: <b>${income}</b>\n"
        f"Осталось дней: <b>{remaining}</b>\n\n"
        f"💰 Начислено: <b>${earned:.2f}</b>\n"
        f"⚠️ Штрафы: <b>${penalty:.2f}</b>\n"
        f"💵 Чистый доход: <b>${net:.2f}</b>\n\n"
        f"🕒 Московское время: <code>{now_msk.strftime('%H:%M:%S')}</code>\n"
        f"⏳ До полуночи: <b>{hours_left:.1f} ч.</b>"
    )

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user["active"]:
        await callback.answer("Нет активной услуги.", show_alert=True)
        return

    earned = user["total_earned"]
    penalty = user["total_penalty"]
    net = earned - penalty
    daily = DAILY_INCOME[user["category"]]

    text = (
        f"💰 <b>Твой баланс</b>\n\n"
        f"Начислено за работу: <b>${earned:.2f}</b>\n"
        f"Штрафы: <b>-${penalty:.2f}</b>\n"
        f"──────────────────\n"
        f"<b>Чистый доход:</b> <b>${net:.2f}</b>\n\n"
        f"Доход в день: ${daily}"
    )

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user["active"]:
        await callback.answer("Нет активной услуги.", show_alert=True)
        return

    remaining = calculate_remaining(user)
    days_worked = SERVICE_DAYS - remaining
    progress = int((days_worked / SERVICE_DAYS) * 100)

    text = (
        f"📅 <b>Статистика услуги</b>\n\n"
        f"Отработано дней: <b>{days_worked}</b> из {SERVICE_DAYS}\n"
        f"Осталось: <b>{remaining}</b> дней\n"
        f"Прогресс: <b>{progress}%</b>\n\n"
        f"Продолжай отмечаться ежедневно!"
    )

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "help")
async def show_help(callback: CallbackQuery):
    text = (
        f"ℹ️ <b>Как пользоваться ботом</b>\n\n"
        f"✅ Каждый день нажимай <b>«РАБОТАЮ»</b> до 23:59 по Москве\n"
        f"⚠️ За пропуск дня — штраф ${PENALTY}\n"
        f"⏳ Услуга длится ровно 30 дней\n"
        f"💵 Чем чаще отмечаешься — тем выше чистый доход\n\n"
        f"После окончания услуги напиши /start для выбора новой."
    )

    await send_with_banner(callback.from_user.id, text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "support")
async def show_support(callback: CallbackQuery):
    text = (
        f"🛠 <b>Поддержка</b>\n\n"
        f"По всем вопросам и проблемам пиши администратору:\n\n"
        f"👤 @muteel   ← замени на свой username\n\n"
        f"Опиши проблему максимально подробно."
    )

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

    user = get_user(user_id)
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

    income = DAILY_INCOME[user["category"]]
    add_earnings(user_id, income)
    update_checkin(user_id, datetime.now(TIMEZONE).isoformat())

    remaining = calculate_remaining(user) - 1

    if remaining <= 0:
        deactivate_user(user_id)
        text = f"✅ <b>Отлично!</b> Ты получил <b>${income}</b> за сегодня.\n\n🎉 Твой 30-дневный период завершён!"
    else:
        text = f"✅ Ты получил <b>${income}</b> за сегодня.\nОсталось дней: <b>{remaining}</b>"

    await send_with_banner(user_id, text, reply_markup=main_menu())
    await callback.answer("Успешно начислено!")


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
    print("✅ Бот успешно запущен на Bothost.ru")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
