from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from flask import Flask, request
import requests, logging, asyncio, os
from threading import Thread

# Безопасность: токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например: https://botai-production-bf8e.up.railway.app/webhook

API_URL = "https://router.huggingface.co/novita/v3/openai/chat/completions"
MODEL_NAME = "deepseek/deepseek-r1-turbo"

# Flask-приложение
app = Flask(__name__)

# Telegram Application
bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

logging.basicConfig(level=logging.INFO)

# Функция запроса к DeepSeek
def query_deepseek(message):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": message}]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return f"[Ошибка API: {response.status_code}]"

MAX_LENGTH = 4096

# Обработка сообщений Telegram
async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.chat.send_action(action="typing")
    reply = query_deepseek(user_message)
    for i in range(0, len(reply), MAX_LENGTH):
        await update.message.reply_text(reply[i:i + MAX_LENGTH])

# Добавляем хендлер
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask route для webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    bot_app.update_queue.put_nowait(
        bot_app.bot._parse_update(request.get_json(), bot_app.bot)
    )
    return "ok"

# Простая проверка
@app.route("/")
def index():
    return "Bot is running!"

# Асинхронная инициализация и установка webhook
async def main():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook установлен: {WEBHOOK_URL}")

# Точка входа
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Запускаем Flask в отдельном потоке
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))).start()

    # Запускаем Telegram-бота
    loop.create_task(main())
    loop.run_forever()
