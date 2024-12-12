from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from db.database import db

description = "Manage your coins, claim daily rewards, and send coins to others"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for coins command - manages user coins"""
    try:
        message_parts = update.message.text.split()
        subcommand = message_parts[1].lower() if len(message_parts) > 1 else "balance"
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        # Get or create user
        db.users.get_user(user_id, username)
        
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
        user = db.users.get_user(user_id)
        
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
        user = db.users.get_user(user_id)
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
        db.users.update_user_coins(user_id, daily_amount)
        db.users.update_last_daily(user_id)
        
        # Record transaction
        db.transactions.add_transaction(
            user_id=user_id,
            amount=daily_amount,
            type_='daily',
            description='Daily reward claimed'
        )
        
        # Get updated user data
        updated_user = db.users.get_user(user_id)
        
        success_msg = (
            "*✅ Daily Reward Claimed!*\n\n"
            f"Reward: `+{daily_amount} coins`\n"
            f"Current Balance: `{updated_user['coins']} coins`"
        )
        await update.message.reply_text(success_msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error claiming daily reward: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def send_coins(update, recipient_username, amount):
    """Send coins to another user"""
    try:
        sender_id = str(update.effective_user.id)
        sender = db.users.get_user(sender_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive", parse_mode=ParseMode.MARKDOWN)
            return
        
        if sender['coins'] < amount:
            await update.message.reply_text(
                f"❌ Insufficient coins. Your balance: `{sender['coins']} coins`", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Find recipient by username
        recipient = db.users.find_user_by_username(recipient_username)
        if not recipient:
            await update.message.reply_text(
                "❌ Recipient not found. Make sure they have used the bot at least once.", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if recipient['user_id'] == sender_id:
            await update.message.reply_text(
                "❌ You cannot send coins to yourself", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        recipient_id = recipient['user_id']
        
        # Transfer coins
        db.users.update_user_coins(sender_id, -amount)
        db.users.update_user_coins(recipient_id, amount)
        
        # Record transactions
        db.transactions.add_transaction(
            user_id=sender_id, 
            amount=-amount, 
            type_='send', 
            description=f"Sent coins to @{recipient_username}"
        )
        
        db.transactions.add_transaction(
            user_id=recipient_id, 
            amount=amount, 
            type_='receive', 
            description=f"Received coins from @{update.effective_user.username}"
        )
        
        # Get updated sender data
        updated_sender = db.users.get_user(sender_id)
        
        success_msg = (
            "*💸 Coins Sent Successfully!*\n\n"
            f"Sent: `{amount} coins` to @{recipient_username}\n"
            f"Current Balance: `{updated_sender['coins']} coins`"
        )
        await update.message.reply_text(success_msg, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending coins: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def show_history(update):
    """Show user's transaction history"""
    try:
        user_id = str(update.effective_user.id)
        transactions = db.transactions.get_transactions(user_id)
        
        if transactions:
            history_msg = "*📜 Recent Transactions*\n\n"
            for tx in transactions:
                emoji = "➕" if tx['amount'] > 0 else "➖"
                amount = abs(tx['amount'])
                date = tx['created_at'].strftime("%Y-%m-%d %H:%M")
                history_msg += f"{emoji} `{amount} coins` - {tx['description']} ({date})\n"
        else:
            history_msg = "*📜 Transaction History*\n\nNo transactions found."
            
        # Get current balance
        user = db.users.get_user(user_id)
        history_msg += f"\nCurrent Balance: `{user['coins']} coins`"
            
        await update.message.reply_text(history_msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error showing history: {str(e)}", parse_mode=ParseMode.MARKDOWN)