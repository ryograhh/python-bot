# commands/coins.py
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import mysql.connector
from datetime import datetime, timedelta
from db.database import get_database_connection

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for coins command - manages user coins"""
    try:
        message_parts = update.message.text.split()
        subcommand = message_parts[1].lower() if len(message_parts) > 1 else "balance"
        
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        connection = get_database_connection()
        if not connection:
            await update.message.reply_text("❌ Database connection error", parse_mode=ParseMode.MARKDOWN)
            return
        
        cursor = connection.cursor(dictionary=True)
        
        # Disable safe updates
        cursor.execute("SET SQL_SAFE_UPDATES = 0")
        
        try:
            # Create user if doesn't exist
            cursor.execute("""
                INSERT IGNORE INTO users (user_id, username) 
                VALUES (%s, %s)
            """, (user_id, username))
            connection.commit()
            
            if subcommand == "balance":
                await show_balance(update, cursor)
            elif subcommand == "daily":
                await claim_daily(update, cursor, connection)
            elif subcommand == "send" and len(message_parts) >= 4:
                try:
                    recipient = message_parts[2].replace("@", "")
                    amount = int(message_parts[3])
                    await send_coins(update, cursor, connection, recipient, amount)
                except ValueError:
                    await update.message.reply_text("❌ Invalid amount specified", parse_mode=ParseMode.MARKDOWN)
            elif subcommand == "history":
                await show_history(update, cursor)
            else:
                usage_msg = (
                    "*🟡 Coin System Commands*\n\n"
                    "`coins` - Show your balance\n"
                    "`coins daily` - Claim daily reward (5 coins)\n"
                    "`coins send @user amount` - Send coins to user\n"
                    "`coins history` - Show your transaction history"
                )
                await update.message.reply_text(usage_msg, parse_mode=ParseMode.MARKDOWN)
        
        finally:
            # Re-enable safe updates
            cursor.execute("SET SQL_SAFE_UPDATES = 1")
            cursor.close()
            connection.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def show_balance(update, cursor):
    """Show user's coin balance"""
    try:
        user_id = update.effective_user.id
        cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            balance_msg = (
                "*🏦 Your Coin Balance*\n\n"
                f"Balance: `{result['coins']} coins`"
            )
            await update.message.reply_text(balance_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Error fetching balance", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error showing balance: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def claim_daily(update, cursor, connection):
    """Claim daily reward"""
    try:
        user_id = update.effective_user.id
        daily_amount = 5  # Daily reward amount set to 5 coins
        
        cursor.execute("SELECT last_daily FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result['last_daily'] is not None:
            last_claim = result['last_daily']
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
        cursor.execute("""
            UPDATE users 
            SET coins = coins + %s, last_daily = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (daily_amount, user_id))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (%s, %s, 'daily', 'Daily reward claimed')
        """, (user_id, daily_amount))
        
        connection.commit()
        
        await update.message.reply_text(
            f"✅ You claimed your daily reward of `{daily_amount} coins`!",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        connection.rollback()
        await update.message.reply_text(f"❌ Error claiming daily reward: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def send_coins(update, cursor, connection, recipient_username, amount):
    """Send coins to another user"""
    try:
        sender_id = update.effective_user.id
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Check sender's balance
        cursor.execute("SELECT coins FROM users WHERE user_id = %s", (sender_id,))
        sender = cursor.fetchone()
        
        if not sender or sender['coins'] < amount:
            await update.message.reply_text("❌ Insufficient coins", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Find recipient
        cursor.execute("SELECT user_id, username FROM users WHERE username = %s", (recipient_username,))
        recipient = cursor.fetchone()
        
        if not recipient:
            await update.message.reply_text("❌ Recipient not found", parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            # Transfer coins
            cursor.execute(
                "UPDATE users SET coins = coins - %s WHERE user_id = %s", 
                (amount, sender_id)
            )
            cursor.execute(
                "UPDATE users SET coins = coins + %s WHERE user_id = %s", 
                (amount, recipient['user_id'])
            )
            
            # Record transactions
            cursor.execute("""
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (%s, %s, 'send', %s),
                       (%s, %s, 'receive', %s)
            """, (
                sender_id, -amount, f"Sent coins to @{recipient_username}",
                recipient['user_id'], amount, f"Received coins from @{update.effective_user.username}"
            ))
            
            connection.commit()
            
            await update.message.reply_text(
                f"✅ Successfully sent `{amount} coins` to @{recipient_username}",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            connection.rollback()
            await update.message.reply_text(f"❌ Error during transfer: {str(e)}", parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending coins: {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def show_history(update, cursor):
    """Show user's transaction history"""
    try:
        user_id = update.effective_user.id
        cursor.execute("""
            SELECT amount, type, description, created_at 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 5
        """, (user_id,))
        transactions = cursor.fetchall()
        
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