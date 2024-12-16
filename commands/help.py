# commands/help.py
import logging

logger = logging.getLogger(__name__)

async def handle(update, context):
    try:
        help_message = (
            "🤖 Available Commands:\n\n"
            "You can use commands with or without the / prefix\n\n"
            "• start - Start/restart the bot\n"
            "• help - Show this help message\n"
            "\nMore commands coming soon!"
        )
        
        await update.message.reply_text(help_message)
        logger.info(f"Help command executed by user: {update.effective_user.username or update.effective_user.first_name}")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")