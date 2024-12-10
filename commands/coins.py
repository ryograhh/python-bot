from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from storage.storage import storage

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for coins command - manages user coins"""
    try:
        message_parts = update.message.text.split()
        subcommand = message_parts[1].lower() if len(message_parts) > 1 else "balance"
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        # Get or create user
        storage.get_user(user_id, username)
        
        if subcommand == "balance":
            await show_balance(update)
        elif subcommand == "daily":
            await claim_daily(update)
        elif subcommand == "send" and len(message_parts) >= 4:
            try:
                recipient = message_parts[2].replace("@", "")
                amount = int(message_parts[3])
                await send_coins(update, recipient, amount)
            except ValueError:
                await update.message.reply_text("❌ Invalid amount specified", parse_mode=ParseMode.MARKDOWN)
        elif subcommand == "history":
            await show_history(update)
        else:
            usage_msg = (
                "*🟡 Coin System Commands*\n\n"
                "`coins` - Show your balance\n"
                "`coins daily` - Claim daily reward (5 coins)\n"
                "`coins send @user amount` - Send coins to user\n"
                "`coins history` - Show your transaction history"
            )
            await update.message.reply_text(usage_msg, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def show_balance(update):
    """Show user's coin balance"""
    try:
        user_id = str(update.effective_user.id)
        user = storage.get_user(user_id)
        
        balance_msg = (
            "*🏦 Your Coin Balance*\n\n"
            f"Balance: `{user['coins']} coins`"
        )
        await update.message.reply_text(balance_msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error showing balance: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def claim_daily(update):
    """Claim daily reward"""
    try:
        user_id = str(update.effective_user.id)
        user = storage.get_user(user_id)
        daily_amount = 5  # Daily reward amount
        
        if user['last_daily']:
            last_claim = user['last_daily']
            next_claim = last_claim + timedelta(days=1)
            
            if datetime.now() < next_claim:
                time_left = next_claim - datetime.now()
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                await update.message.reply_text(
                    f"❌ You can claim your daily reward in: `{hours}h {minutes}m`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Update user's coins and last_daily
        storage.update_user_coins(user_id, daily_amount)
        storage.update_last_daily(user_id)
        
        # Record transaction
        storage.add_transaction(user_id, daily_amount, 'daily', 'Daily reward claimed')
        
        await update.message.reply_text(
            f"✅ You claimed your daily reward of `{daily_amount} coins`!",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error claiming daily reward: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def send_coins(update, recipient_username, amount):
    """Send coins to another user"""
    try:
        sender_id = str(update.effective_user.id)
        sender = storage.get_user(sender_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive", parse_mode=ParseMode.MARKDOWN)
            return
        
        if sender['coins'] < amount:
            await update.message.reply_text("❌ Insufficient coins", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Find recipient by username
        recipient_id = None
        for uid, udata in storage.users.items():
            if udata['username'].lower() == recipient_username.lower():
                recipient_id = uid
                break
        
        if not recipient_id:
            await update.message.reply_text("❌ Recipient not found", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Transfer coins
        storage.update_user_coins(sender_id, -amount)
        storage.update_user_coins(recipient_id, amount)
        
        # Record transactions
        storage.add_transaction(
            sender_id, 
            -amount, 
            'send', 
            f"Sent coins to @{recipient_username}"
        )
        storage.add_transaction(
            recipient_id, 
            amount, 
            'receive', 
            f"Received coins from @{update.effective_user.username}"
        )
        
        await update.message.reply_text(
            f"✅ Successfully sent `{amount} coins` to @{recipient_username}",
            parse_mode=ParseMode.MARKDOWN
        )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending coins: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def show_history(update):
    """Show user's transaction history"""
    try:
        user_id = str(update.effective_user.id)
        transactions = storage.get_transactions(user_id)
        
        if transactions:
            history_msg = "*📜 Recent Transactions*\n\n"
            for tx in transactions:
                emoji = "➕" if tx['amount'] > 0 else "➖"
                amount = abs(tx['amount'])
                date = tx['created_at'].strftime("%Y-%m-%d %H:%M")
                history_msg += f"{emoji} `{amount} coins` - {tx['description']} ({date})\n"
        else:
            history_msg = "*📜 Transaction History*\n\nNo transactions found."
            
        await update.message.reply_text(history_msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error showing history: {str(e)}", parse_mode=ParseMode.MARKDOWN)