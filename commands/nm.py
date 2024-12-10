import base64
import json
from Crypto.Cipher import AES
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import aiohttp
import io
from db.database import get_database_connection

DECRYPT_COST = 2  # Cost in coins for each decryption attempt

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the nm command - decrypts encrypted content from text or .nm files"""
    try:
        # Check if user has enough coins first
        connection = get_database_connection()
        if not connection:
            await update.message.reply_text("❌ Database connection error", parse_mode=ParseMode.MARKDOWN)
            return
            
        cursor = connection.cursor(dictionary=True)
        user_id = update.effective_user.id
        
        # Check user's balance
        cursor.execute("SELECT coins FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await update.message.reply_text("❌ Please use the coins command first to create your account", parse_mode=ParseMode.MARKDOWN)
            cursor.close()
            connection.close()
            return
            
        if user['coins'] < DECRYPT_COST:
            await update.message.reply_text(
                f"❌ Insufficient coins. Decryption costs `{DECRYPT_COST}` coins. Your balance: `{user['coins']}` coins",
                parse_mode=ParseMode.MARKDOWN
            )
            cursor.close()
            connection.close()
            return

        # Deduct coins first
        cursor.execute("""
            UPDATE users SET coins = coins - %s WHERE user_id = %s
        """, (DECRYPT_COST, user_id))
        connection.commit()

        try:
            if update.message.document and update.message.document.file_name.endswith('.nm'):
                # Handle .nm file
                file = await context.bot.get_file(update.message.document.file_id)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(file.file_path) as response:
                        if response.status == 200:
                            encrypted_content = await response.text()
                            await process_decryption(update, encrypted_content, user_id)
                        else:
                            # Return coins on failure
                            cursor.execute("""
                                UPDATE users SET coins = coins + %s WHERE user_id = %s
                            """, (DECRYPT_COST, user_id))
                            connection.commit()
                            await update.message.reply_text(
                                "```\n❌ Error: Could not download file. Coins have been returned.\n```",
                                parse_mode=ParseMode.MARKDOWN
                            )
                
            elif update.message.text:
                # Handle text input
                message_parts = update.message.text.split(" ", 1)
                if len(message_parts) < 2:
                    # Return coins if no content provided
                    cursor.execute("""
                        UPDATE users SET coins = coins + %s WHERE user_id = %s
                    """, (DECRYPT_COST, user_id))
                    connection.commit()
                    usage_msg = (
                        "*NM Decryption Tool*\n\n"
                        f"Cost: `{DECRYPT_COST}` coins per decryption\n\n"
                        "Usage:\n"
                        "1. Send text: `nm {encrypted_content}`\n"
                        "2. Send a file with `.nm` extension"
                    )
                    await update.message.reply_text(usage_msg, parse_mode=ParseMode.MARKDOWN)
                    return
                
                encrypted_content = message_parts[1]
                await process_decryption(update, encrypted_content, user_id)

        except Exception as e:
            # Return coins on any error
            cursor.execute("""
                UPDATE users SET coins = coins + %s WHERE user_id = %s
            """, (DECRYPT_COST, user_id))
            connection.commit()
            error_msg = f"```\n❌ Error: {str(e)}\nCoins have been returned.\n```"
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
        
        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        await update.message.reply_text(f"```\n❌ Error: {str(e)}\n```", parse_mode=ParseMode.MARKDOWN)

async def process_decryption(update, encrypted_content, user_id):
    """Process the decryption and send formatted results"""
    try:
        key = base64.b64decode("X25ldHN5bmFfbmV0bW9kXw==")
        decrypted_message = handle_nm(encrypted_content, key)

        if decrypted_message:
            # Format the decrypted content
            decrypted_content = "\n".join(decrypted_message)
            
            # Create a beautiful markdown message with cost info
            formatted_msg = (
                "*🔓 Decryption Results*\n"
                f"Cost: `-{DECRYPT_COST}` coins\n\n"
                "```\n"
                f"{decrypted_content}\n"
                "```"
            )
            
            # Send the formatted message
            await update.message.reply_text(
                formatted_msg,
                parse_mode=ParseMode.MARKDOWN
            )

            # Save and send as file
            temp_file_path = "decrypted.txt"
            with open(temp_file_path, "w", encoding="utf-8") as file:
                file.write(decrypted_content)

            # Send as document with formatted caption
            file_size_kb = os.path.getsize(temp_file_path) / 1024
            caption = (
                "📄 *Decrypted Content File*\n"
                f"Size: `{file_size_kb:.2f} KB`"
            )
            
            with open(temp_file_path, "rb") as file:
                await update.message.reply_document(
                    document=file,
                    filename="decrypted.txt",
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )

            # Cleanup
            os.remove(temp_file_path)

        else:
            # Return coins if decryption yielded no content
            connection = get_database_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("""
                    UPDATE users SET coins = coins + %s WHERE user_id = %s
                """, (DECRYPT_COST, user_id))
                connection.commit()
                cursor.close()
                connection.close()
            
            await update.message.reply_text(
                "```\n❌ Decryption yielded no content. Coins have been returned.\n```",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        # Return coins on error
        connection = get_database_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users SET coins = coins + %s WHERE user_id = %s
            """, (DECRYPT_COST, user_id))
            connection.commit()
            cursor.close()
            connection.close()
            
        error_msg = f"```\n❌ Decryption Error: {str(e)}\nCoins have been returned.\n```"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)

def decrypt_aes_ecb_128(ciphertext, key):
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(ciphertext)
    return decrypted

def parse_config(data):
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