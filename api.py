from telegram.ext import ApplicationBuilder, MessageHandler, filters
import os
import importlib
import glob
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def load_commands():
    commands = {}
    # Get all python files from commands directory using Path for cross-platform compatibility
    command_files = list(Path('commands').glob('*.py'))
    
    for file in command_files:
        if file.stem != '__init__':
            # Get command name from filename (without .py)
            command_name = file.stem
            
            try:
                # Import the module dynamically
                module = importlib.import_module(f'commands.{command_name}')
                
                # Get the main handler function
                if hasattr(module, 'handle'):
                    commands[command_name] = module.handle
            except ImportError as e:
                print(f"Error loading command {command_name}: {e}")
    
    return commands

async def message_handler(update, context):
    # Handle document messages for both .nm and .sks files
    if update.message.document:
        commands = load_commands()
        file_name = update.message.document.file_name.lower()
        
        if file_name.endswith('.nm') and 'nm' in commands:
            return await commands['nm'](update, context)
        elif file_name.endswith('.sks') and 'sks' in commands:
            return await commands['sks'](update, context)
        return

    # Handle text messages
    if update.message.text:
        message = update.message.text
        # Get first word from message
        command = message.split()[0].lower()
        
        # Get all available commands
        commands = load_commands()
        
        # Execute command if it exists
        if command in commands:
            return await commands[command](update, context)
        
        # Optional: Handle unknown commands
        await update.message.reply_text(f"Unknown command: {command}")

def setup_bot():
    # Get token from environment variable
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        raise ValueError("No token provided. Please set TELEGRAM_BOT_TOKEN environment variable.")

    # Create application instance
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers for both text messages and documents
    application.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, message_handler))

    # Start the bot
    print("Bot is starting...")
    application.run_polling()
    return application