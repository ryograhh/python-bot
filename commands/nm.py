from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler
from db.mongodb import db
import random
from datetime import datetime, timedelta

# Game settings
MIN_BET = 1
MAX_BET = 100
COOLDOWN_SECONDS = 30

# Color multipliers
MULTIPLIERS = {
    'red': 2,    # 2x for red
    'green': 3,  # 3x for green
    'blue': 5    # 5x for blue (rare)
}

# Color probabilities (must sum to 100)
PROBABILITIES = {
    'red': 50,    # 50% chance
    'green': 35,  # 35% chance
    'blue': 15    # 15% chance
}

# Store user cooldowns in memory (no need to persist)
user_cooldowns = {}

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the color game command"""
    try:
        message_parts = update.message.text.split()
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        # Get or create user
        user = db.get_user(user_id, username)
        
        if len(message_parts) == 1:
            # Show game info and instructions
            info_msg = (
                "*🎨 Color Gambling Game*\n\n"
                f"Minimum bet: `{MIN_BET}` coins\n"
                f"Maximum bet: `{MAX_BET}` coins\n\n"
                "*Multipliers:*\n"
                "🔴 Red: 2x (50% chance)\n"
                "💚 Green: 3x (35% chance)\n"
                "🔵 Blue: 5x (15% chance)\n\n"
                "*How to play:*\n"
                "Use command: `color <amount> <color>`\n"
                "Example: `color 10 red`\n\n"
                f"Cooldown: {COOLDOWN_SECONDS} seconds between games"
            )
            await update.message.reply_text(info_msg, parse_mode=ParseMode.MARKDOWN)
            return

        if len(message_parts) != 3:
            await update.message.reply_text(
                "❌ Invalid format. Use: `color <amount> <color>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Check cooldown
        if user_id in user_cooldowns:
            time_diff = datetime.now() - user_cooldowns[user_id]
            if time_diff.total_seconds() < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - time_diff.total_seconds())
                await update.message.reply_text(
                    f"❌ Please wait `{remaining}` seconds before playing again",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

        try:
            bet_amount = int(message_parts[1])
            color = message_parts[2].lower()
        except ValueError:
            await update.message.reply_text(
                "❌ Bet amount must be a number",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if color not in MULTIPLIERS:
            await update.message.reply_text(
                "❌ Invalid color. Choose: `red`, `green`, or `blue`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if bet_amount < MIN_BET or bet_amount > MAX_BET:
            await update.message.reply_text(
                f"❌ Bet must be between `{MIN_BET}` and `{MAX_BET}` coins",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if user['coins'] < bet_amount:
            await update.message.reply_text(
                "❌ Insufficient coins for this bet",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Update cooldown
        user_cooldowns[user_id] = datetime.now()

        # Deduct bet amount
        db.update_user_coins(user_id, -bet_amount)
        db.add_transaction(user_id, -bet_amount, 'game', f'Color game bet on {color}')

        # Generate result based on probabilities
        result = random.choices(
            list(PROBABILITIES.keys()),
            weights=list(PROBABILITIES.values()),
            k=1
        )[0]

        # Determine if user won
        won = color == result
        
        # Calculate winnings if won
        if won:
            winnings = bet_amount * MULTIPLIERS[color]
            db.update_user_coins(user_id, winnings)
            db.add_transaction(user_id, winnings, 'game', f'Color game win on {color}')
            net_profit = winnings - bet_amount
        else:
            net_profit = -bet_amount

        # Get color emoji
        color_emojis = {'red': '🔴', 'green': '💚', 'blue': '🔵'}
        result_emoji = color_emojis[result]
        chosen_emoji = color_emojis[color]

        # Create result message
        if won:
            result_msg = (
                f"*🎨 Color Game Result - {chosen_emoji}*\n\n"
                f"Result: {result_emoji}\n"
                f"Bet: `{bet_amount}` coins on {chosen_emoji}\n"
                f"Multiplier: `{MULTIPLIERS[color]}x`\n"
                f"Winnings: `+{winnings}` coins\n"
                f"Net Profit: `+{net_profit}` coins\n\n"
                "🎉 Congratulations! You won!"
            )
        else:
            result_msg = (
                f"*🎨 Color Game Result - {chosen_emoji}*\n\n"
                f"Result: {result_emoji}\n"
                f"Bet: `{bet_amount}` coins on {chosen_emoji}\n"
                f"Net Loss: `{net_profit}` coins\n\n"
                "😢 Better luck next time!"
            )

        # Show updated balance
        user = db.get_user(user_id)
        result_msg += f"\n\nCurrent Balance: `{user['coins']}` coins"

        await update.message.reply_text(result_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)