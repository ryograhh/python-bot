from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import base64
import json
from Crypto.Cipher import AES
import os
import tempfile

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
    """Handler for the nm command"""
    try:
        # Check if there's a file attached
        if update.message.document and update.message.document.file_name.endswith('.nm'):
            # Get file from Telegram
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Download the file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                await file.download_to_memory(temp_file)
                temp_file_path = temp_file.name

            # Read the file content
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                encrypted_content = f.read().strip()
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
        else:
            # Get encrypted content from message text
            message_parts = update.message.text.split(maxsplit=1)
            if len(message_parts) < 2:
                await update.message.reply_text(
                    "❌ No encrypted content provided.\n\nUsage:\n`nm <encrypted_content>`\nor send a .nm file",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            encrypted_content = message_parts[1]

        # Decrypt the content
        key = base64.b64decode("X25ldHN5bmFfbmV0bW9kXw==")
        decrypted_messages = handle_nm(encrypted_content, key)

        if not decrypted_messages:
            await update.message.reply_text("❌ Decryption yielded no content.")
            return

        # Format the decrypted content
        decrypted_content = "\n".join(decrypted_messages)

        # Send the decrypted content as a message
        await update.message.reply_text(
            f"*🔓 Decrypted Content:*\n\n{decrypted_content}",
            parse_mode=ParseMode.MARKDOWN
        )

        # Save and send as a file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(decrypted_content)
            temp_file_path = temp_file.name

        # Send the file
        with open(temp_file_path, 'rb') as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename='decrypted.txt',
                caption='🔓 Decrypted content saved in this file'
            )

        # Clean up
        os.unlink(temp_file_path)

        # Send completion message with file size
        file_size_kb = len(decrypted_content.encode('utf-8')) / 1024
        await update.message.reply_text(
            f"✅ Decryption complete!\nFile size: `{file_size_kb:.2f}` KB",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )