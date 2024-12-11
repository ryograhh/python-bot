from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os
from pathlib import Path
import importlib.util

async def get_available_commands():
    """Dynamically get all available commands from the commands folder"""
    commands = []
    commands_dir = Path(__file__).parent
    
    for file in commands_dir.glob('*.py'):
        if file.stem not in ['__init__', 'start']:  # Exclude init and start command
            try:
                # Import the module to get its description if available
                spec = importlib.util.spec_from_file_location(file.stem, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get command description if available, otherwise use command name
                description = getattr(module, 'description', file.stem)
                commands.append({
                    'name': file.stem,
                    'description': description
                })
            except Exception as e:
                print(f"Error loading command {file.stem}: {e}")
    
    return sorted(commands, key=lambda x: x['name'])

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the start command - sends welcome message and command list"""
    try:
        # Get user info
        user = update.effective_user
        first_name = user.first_name
        username = user.username or "there"

        # Get available commands
        commands = await get_available_commands()

        # Create welcome message
        welcome_msg = (
            f"👋 *Welcome @{username}!*\n\n"
            "I'm your Telegram bot assistant. Here are the available commands:\n\n"
        )

        # Add coins command info (if available)
        if any(cmd['name'] == 'coins' for cmd in commands):
            welcome_msg += (
                "*💰 Economy System:*\n"
                "• Use `/coins` to check your balance\n"
                "• Daily rewards available with `/coins daily`\n"
                "• Send coins to friends with `/coins send @user amount`\n\n"
            )

        # Add color game info (if available)
        if any(cmd['name'] == 'color' for cmd in commands):
            welcome_msg += (
                "*🎮 Games:*\n"
                "• `/color` - Gambling game with colors\n"
                "  - Red (2x, 50% chance)\n"
                "  - Green (3x, 35% chance)\n"
                "  - Blue (5x, 15% chance)\n\n"
            )

        # Add nm command info (if available)
        if any(cmd['name'] == 'nm' for cmd in commands):
            welcome_msg += (
                "*🔐 Netmod Decryption:*\n"
                "• `/nm <content>` - Decrypt text (3 coins)\n"
                "• Upload .nm file - Decrypt file (4 coins)\n\n"
            )

        welcome_msg += "*📜 All Available Commands:*\n"
        for cmd in commands:
            # Format each command with its description
            welcome_msg += f"• `/{cmd['name']}` - {cmd['description']}\n"

        # Add usage hint
        welcome_msg += (
            "\n*💡 Tip:* Use `/help <command>` for detailed information about a specific command."
        )

        # Send welcome message
        await update.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )