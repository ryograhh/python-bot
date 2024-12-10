from telegram import Update
from telegram.ext import ContextTypes

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the ping command"""
    await update.message.reply_text('Pong!')
