import os
from datetime import datetime
import pytz

# Основные настройки через переменные окружения
TOKEN = os.getenv("TOKEN")                    # ← будет браться из Bothost
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

# Доходность услуг
DAILY_INCOME = {
    1: 3.4,
    2: 2.0,
    3: 4.0,
    4: 2.8
}

PENALTY = 2.0
SERVICE_DAYS = 30

# Часовой пояс
TIMEZONE = pytz.timezone('Europe/Moscow')
