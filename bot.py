import asyncio
import json
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
# Render автоматически подставляет публичный HTTPS-адрес сервиса в переменную RENDER_EXTERNAL_URL
WEBAPP_URL = os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL", "")

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
    try:
        data = json.loads(message.web_app_data.data)
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
        items_lines = [
            f"{idx}. {item['name']} × {item['qty']} шт. = {item['sum']} ₽"
            for idx, item in enumerate(data.get("items", []), start=1)
        ]
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

        await message.answer(
            "✅ **Ваш заказ принят!** Оператор скоро свяжется с вами для подтверждения.\n\n"
            + receipt,
            parse_mode="Markdown",
        )

        if ADMIN_CHAT_ID:
            await bot.send_message(ADMIN_CHAT_ID, receipt, parse_mode="Markdown")


async def serve_index(request: web.Request):
    return web.FileResponse("index.html")


async def healthcheck(request: web.Request):
    return web.Response(text="OK")


async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    app["bot_task"] = asyncio.create_task(dp.start_polling(bot))


async def on_cleanup(app: web.Application):
    app["bot_task"].cancel()
    await bot.session.close()


def main():
    app = web.Application()
    app.router.add_get("/", serve_index)
    app.router.add_get("/health", healthcheck)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
