from aiogram.types import Message
from config import ADMIN_ID
from database import get_all_users, get_all_active_users

async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    users = get_all_users()
    if not users:
        await message.answer("Нет пользователей")
        return

    text = "👥 **Все пользователи:**\n\n"
    for u in users:
        text += (f"ID: `{u[0]}` | @{u[1]} | Кат.{u[2]} | "
                 f"Зараб: ${u[3]:.2f} | Штраф: ${u[4]:.2f} | "
                 f"Активен: {'✅' if u[5] else '❌'}\n")

    await message.answer(text, parse_mode="Markdown")

async def broadcast(message: Message, bot):
    if not await is_admin(message.from_user.id):
        return

    msg_text = message.text.replace("/broadcast", "").strip()
    if not msg_text:
        await message.answer("Используй: `/broadcast Текст сообщения`")
        return

    users = get_all_active_users()
    success = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 **РАССЫЛКА**\n\n{msg_text}", parse_mode="Markdown")
            success += 1
        except:
            pass

    await message.answer(f"✅ Рассылка отправлена {success} пользователям")
