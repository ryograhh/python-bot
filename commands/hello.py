from telegram import Update
from telegram.ext import ContextTypes

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the hello command"""
    await update.message.reply_text(
        f'Hello {update.effective_user.first_name}! I am your Telegram bot.'
    )