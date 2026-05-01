from datetime import datetime, timedelta
from config import PENALTY, SERVICE_DAYS, TIMEZONE
from database import get_user, update_checkin, add_penalty, deactivate_user, get_all_active_users

async def apply_penalties_and_update(user_id: int):
    """Начисляет штрафы за пропущенные дни при входе пользователя"""
    user = get_user(user_id)
    if not user or not user["active"]:
        return

    last_date = datetime.fromisoformat(user["last_checkin"]).date()
    today = datetime.now(TIMEZONE).date()
    activation_date = datetime.fromisoformat(user["activation_date"]).date()

    # Проверка окончания срока услуги
    days_since_activation = (today - activation_date).days
    if days_since_activation >= SERVICE_DAYS:
        deactivate_user(user_id)
        return

    if last_date == today:
        return  # уже отмечался сегодня

    # Начисляем штрафы за все пропущенные дни
    current = last_date + timedelta(days=1)
    while current < today:
        add_penalty(user_id, PENALTY)
        update_checkin(user_id, current.isoformat())   # фиксируем, чтобы не штрафовать повторно
        current += timedelta(days=1)


async def auto_apply_daily_penalties():
    """Запускается каждый день в 00:00 по Москве — штрафует за вчерашний день"""
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)

    for uid in get_all_active_users():
        user = get_user(uid)
        if not user or not user["active"]:
            continue

        last_date = datetime.fromisoformat(user["last_checkin"]).date()
        activation_date = datetime.fromisoformat(user["activation_date"]).date()

        # Проверка окончания услуги
        if (today - activation_date).days >= SERVICE_DAYS:
            deactivate_user(uid)
            continue

        # Если не отмечался вчера → штраф за вчера
        if last_date < yesterday:
            add_penalty(uid, PENALTY)
            update_checkin(uid, yesterday.isoformat())
