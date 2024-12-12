from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from db.database import db

description = "Redeem admin codes for coins"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for code command - redeems admin codes"""
    try:
        message_parts = update.message.text.split()
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        # Get or create user
        db.users.get_user(user_id, username)

        if len(message_parts) == 1:
            usage_msg = (
                "*🎟️ Admin Code System*\n\n"
                "Use this command to redeem admin codes for coins.\n\n"
                "*Usage:*\n"
                "`code <your_code>` - Redeem an admin code\n\n"
                "Example: `code ABC123XY`"
            )
            await update.message.reply_text(usage_msg, parse_mode=ParseMode.MARKDOWN)
            return

        # Get the code from message
        input_code = message_parts[1].upper()

        # Try to redeem the code
        result = db.admin_codes.use_admin_code(input_code, user_id)

        if result['success']:
            # Add transaction record
            db.transactions.add_transaction(
                user_id=user_id,
                amount=result['coins_added'],
                type_='admin_code',
                description=f"Redeemed code: {input_code}"
            )
            
            # Get updated user data
            user = db.users.get_user(user_id)
            
            success_msg = (
                "*✅ Code Redeemed Successfully!*\n\n"
                f"Coins Added: `+{result['coins_added']}`\n"
                f"Current Balance: `{user['coins']} coins`"
            )
            await update.message.reply_text(success_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            error_msg = (
                "*❌ Code Redemption Failed*\n\n"
                f"Reason: `{result['error']}`"
            )
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )