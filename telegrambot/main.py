from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from flask import Flask, request
import requests, logging, asyncio, os
from threading import Thread
from telegram import Update


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

API_URL = "https://router.huggingface.co/novita/v3/openai/chat/completions"
MODEL_NAME = "deepseek/deepseek-r1-turbo"

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

logging.basicConfig(level=logging.INFO)

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

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.chat.send_action(action="typing")
    reply = query_deepseek(user_message)
    for i in range(0, len(reply), MAX_LENGTH):
        await update.message.reply_text(reply[i:i + MAX_LENGTH])

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

async def telegram_main():
    await bot_app.initialize()
    await bot_app.start()
    # ТОЛЬКО set_webhook, без polling
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook установлен: {WEBHOOK_URL}")
    # не вызывай updater.start_polling()

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(telegram_main())
