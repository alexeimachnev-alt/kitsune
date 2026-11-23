import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

# Вставьте токен бота от @BotFather и публичный HTTPS-адрес вашего Mini App
BOT_TOKEN = os.getenv("BOT_TOKEN", "8000000000:AAH_ВАШ_ТОКЕН_ОТ_BOTFATHER")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ваш-домен.ru/index.html")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "123456789"))  # Ваш Telegram ID или ID группы поваров/менеджеров

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🍣 Открыть меню Kitsune",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Добро пожаловать в **Kitsune — Суши и Пицца**! 🦊🔥\n\n"
        "Нажмите на кнопку ниже, чтобы открыть меню, использовать **500 приветственных баллов** и оформить доставку или самовывоз.",
        reply_markup=kb,
        parse_mode="Markdown",
    )


@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    raw_data = message.web_app_data.data
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        await message.answer("Ошибка чтения данных заказа.")
        return

    user = message.from_user
    user_link = f"@{user.username}" if user.username else f"ID: {user.id}"

    if data.get("type") == "review":
        review_text = data.get("text", "")
        await message.answer("Спасибо! Ваш отзыв передан владельцу ресторана Kitsune. 🦊")
        if ADMIN_CHAT_ID:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"📩 **Новый отзыв владельцу Kitsune**\n"
                f"От: {user.full_name} ({user_link})\n\n"
                f"{review_text}",
                parse_mode="Markdown",
            )
        return

    if data.get("type") == "order":
        items_lines = []
        for idx, item in enumerate(data.get("items", []), start=1):
            items_lines.append(
                f"{idx}. {item['name']} × {item['qty']} шт. = {item['sum']} ₽"
            )
        items_block = "\n".join(items_lines)

        delivery_label = (
            "🚗 Доставка курьером"
            if data.get("deliveryType") == "delivery"
            else "🏪 Самовывоз"
        )

        receipt = (
            f"🍣 **НОВЫЙ ЗАКАЗ — KITSUNE**\n"
            f"Клиент: {user.full_name} ({user_link})\n"
            f"Телефон: `{data.get('phone')}`\n"
            f"Способ: {delivery_label}\n"
            f"Филиал: {data.get('branch')}\n"
            f"Адрес: {data.get('address')}\n"
            f"Комментарий: {data.get('comment') or '—'}\n\n"
            f"**Состав заказа:**\n{items_block}\n\n"
            f"Сумма: {data.get('subtotal')} ₽\n"
            f"Списано баллов: −{data.get('bonusDiscount')} ₽\n"
            f"💰 **Итого к оплате: {data.get('total')} ₽**"
        )

        # Подтверждение клиенту
        await message.answer(
            "✅ **Ваш заказ принят!** Оператор скоро свяжется с вами для подтверждения.\n\n"
            + receipt,
            parse_mode="Markdown",
        )

        # Уведомление менеджеру / на кухню
        if ADMIN_CHAT_ID:
            await bot.send_message(
                ADMIN_CHAT_ID,
                receipt,
                parse_mode="Markdown",
            )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
