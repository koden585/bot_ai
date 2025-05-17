from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from flask import Flask, request
import requests, logging, asyncio
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

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
    update = bot_app.update_queue.put_nowait(
        bot_app.bot._parse_update(request.get_json(), bot_app.bot)
    )
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

async def main():
    await bot_app.initialize()
    await bot_app.start()
    # Установим webhook
    webhook_url = os.getenv("WEBHOOK_URL")
    await bot_app.bot.set_webhook(url=webhook_url)
    print(f"Webhook установлен: {webhook_url}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
