import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {name}! আসসালামু আলাইকুম।\n"
        "আমি এখন ২৪ ঘণ্টা অনলাইন সার্ভারে যুক্ত আছি! বাংলা বা English-এ মেসেজ দিন।"
    )

async def smart_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    name = update.effective_user.first_name

    if any(w in text for w in ["hi", "hello", "হাই", "হ্যালো"]):
        reply = f"Hello {name}! হাই, কেমন আছেন? How can I help you?"
    elif any(w in text for w in ["salam", "সালাম", "আসসালামু"]):
        reply = f"ওয়ালাইকুম আসসালাম {name}! কেমন আছেন?"
    elif any(w in text for w in ["কেমন আছ", "how are you"]):
        reply = "আমি ভালো আছি (I am doing great)! আপনি কেমন আছেন?"
    elif any(w in text for w in ["thanks", "thank you", "ধন্যবাদ"]):
        reply = "You're welcome! আপনাকেও ধন্যবাদ।"
    else:
        reply = f"{name}, আপনি বলেছেন: {update.message.text}"

    await update.message.reply_text(reply)

def main() -> None:
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_reply))
    print("24/7 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
