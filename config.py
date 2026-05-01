TOKEN = "8791127375:AAH8isLmQDMIvBiUbkRxYFsbXDU4f9s3DOM"  # Замени на токен от BotFather

# Доходность услуг (категория -> долларов в день)
DAILY_INCOME = {
    1: 3.4,
    2: 2.0,
    3: 4.0,
    4: 2.8
}

PENALTY = 2.0           # штраф за пропуск дня
SERVICE_DAYS = 30       # длительность услуги в днях
ADMIN_ID = 7762906140    # твой Telegram ID

# Часовой пояс (Москва)
import pytz
TIMEZONE = pytz.timezone('Europe/Moscow')
