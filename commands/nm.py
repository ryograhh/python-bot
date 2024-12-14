from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import base64
import json
from Crypto.Cipher import AES
import os
import tempfile
from db.mongodb import db
from db.models.pastebin import pastebin_db
from handler.pastebinhandler import pastebin_handler
from datetime import datetime

description = "Decrypt Netmod content and save to Pastebin (costs 3-4 coins)"

TEXT_COST = 3 
FILE_COST = 4  

def decrypt_aes_ecb_128(ciphertext, key):
    """Decrypt AES-ECB-128 encrypted content"""
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(ciphertext)
    return decrypted

def parse_config(data):
    """Parse and format decrypted JSON data"""
    result = []
    for key, value in data.items():
        if key.lower() == "note":
            continue
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key.lower() != "note":
                    result.append(f"{sub_key.lower()} {sub_value}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for sub_key, sub_value in item.items():
                        if sub_key.lower() != "note":
                            result.append(f"{sub_key.lower()} {sub_value}")
                else:
                    result.append(f"{key.lower()} {item}")
        else:
            result.append(f"{key.lower()} {value}")
    return result

def handle_nm(encrypted_content, key):
    """Process encrypted content and return decrypted messages"""
    message = []
    try:
        encrypted_text = base64.b64decode(encrypted_content)
        decrypted_text = decrypt_aes_ecb_128(encrypted_text, key)
        decrypted_string = decrypted_text.rstrip(b"\x00").decode('utf-8')

        json_match = None
        if "{" in decrypted_string and "}" in decrypted_string:
            json_match = decrypted_string[decrypted_string.find("{"):decrypted_string.rfind("}") + 1]

        if json_match:
            try:
                json_object = json.loads(json_match)
                message.extend(parse_config(json_object))
            except json.JSONDecodeError as e:
                message.append(f"Error parsing decrypted JSON: {e.msg}")
        else:
            message.append("No valid JSON found after decryption.")

    except Exception as e:
        message.append(f"Error during decryption: {str(e)}")

    return message

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the command execution"""
    try:
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        user = db.get_user(user_id, username)

        # Check if there's a file attached
        is_file = update.message.document and update.message.document.file_name.endswith('.nm')
        cost = FILE_COST if is_file else TEXT_COST

        # Check if user has enough coins
        if user['coins'] < cost:
            await update.message.reply_text(
                f"❌ Insufficient coins! You need `{cost}` coins for this operation.\n"
                f"Your balance: `{user['coins']}` coins",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Process file or text input
        if is_file:
            file = await context.bot.get_file(update.message.document.file_id)
            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                await file.download_to_memory(temp_file)
                temp_file_path = temp_file.name

            with open(temp_file_path, 'r', encoding='utf-8') as f:
                encrypted_content = f.read().strip()
            
            os.unlink(temp_file_path)
        else:
            # Get encrypted content from message text
            message_parts = update.message.text.split(maxsplit=1)
            if len(message_parts) < 2:
                await update.message.reply_text(
                    "*🔐 Netmod Decryption Service*\n\n"
                    "Usage:\n"
                    "1. Text command: `nm <encrypted_content>`\n"
                    "   Cost: `3 coins`\n\n"
                    "2. File upload: Send `.nm` file\n"
                    "   Cost: `4 coins`\n\n"
                    f"Your balance: `{user['coins']}` coins",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            encrypted_content = message_parts[1]

        # Deduct coins and record transaction
        db.update_user_coins(user_id, -cost)
        db.add_transaction(
            user_id, 
            -cost, 
            'service', 
            f'Netmod decryption ({("file" if is_file else "text")} mode)'
        )

        # Decrypt the content
        key = base64.b64decode("X25ldHN5bmFfbmV0bW9kXw==")
        decrypted_messages = handle_nm(encrypted_content, key)

        if not decrypted_messages:
            await update.message.reply_text("❌ Decryption yielded no content.")
            return

        # Format and prepare content for Pastebin
        decrypted_content = "\n".join(decrypted_messages)
        paste_title = f"Decrypted_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # First store in MongoDB
        entry_id = pastebin_db.create_entry(
            user_id=user_id,
            content=decrypted_content,
            title=paste_title,
            username=username
        )

        # Create Pastebin entry
        paste_url = pastebin_handler.create_paste(
            content=decrypted_content,
            title=f"Decrypted Content for {username}",
            expiration='1M',  # 1 month expiration
            private=1  # unlisted
        )

        if paste_url:
            # Update MongoDB with Pastebin URL
            pastebin_db.update_paste_url(entry_id, paste_url)
            
            # Send success message with Pastebin link
            file_size_kb = len(decrypted_content.encode('utf-8')) / 1024
            await update.message.reply_text(
                f"✅ Decryption complete!\n\n"
                f"🔗 View result: {paste_url}\n\n"
                f"📊 Details:\n"
                f"- Size: `{file_size_kb:.2f}` KB\n"
                f"- Cost: `-{cost}` coins\n"
                f"- Balance: `{user['coins'] - cost}` coins\n\n"
                f"🕒 Link expires in 1 month",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Fallback to direct message if Pastebin fails
            await update.message.reply_text(
                "*🔓 Decrypted Content:*\n\n"
                f"```\n{decrypted_content}\n```\n\n"
                "⚠️ Note: Pastebin service unavailable - showing content directly\n"
                f"Cost: `-{cost}` coins\n"
                f"Balance: `{user['coins'] - cost}` coins",
                parse_mode=ParseMode.MARKDOWN
            )

        # Get updated user balance
        updated_user = db.get_user(user_id)
        
        # Log the transaction
        db.add_transaction(
            user_id,
            -cost,
            'netmod_decrypt',
            f'Netmod decryption to Pastebin - {paste_title}'
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )