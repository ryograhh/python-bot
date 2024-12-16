# commands/start.py
import logging

logger = logging.getLogger(__name__)

async def handle(update, context):
    """Handle the /start command"""
    try:
        user = update.effective_user
        first_name = user.first_name if user else "there"
        
        welcome_message = (
            f"👋 Hello {first_name}!\n\n"
            "Welcome to your bot assistant. Here are the available commands:\n\n"
            "• start - Show this welcome message\n"
            "• help - Show available commands\n\n"
            "You can use commands with or without the / prefix.\n"
            "For example, both 'start' and '/start' will work!"
        )
        
        await update.message.reply_text(welcome_message)
        logger.info(f"Start command executed by user {first_name} ({user.id if user else 'unknown'})")
        
    except Exception as e:
        error_msg = f"Error in start command: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(
            "Sorry, there was an error processing your command. Please try again."
        )