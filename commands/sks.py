from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import json
import hashlib
from Crypto.Cipher import AES
from base64 import b64decode, b64encode
import os
import tempfile
from db.mongodb import db

# Cost settings
TEXT_COST = 4  # Cost for text-based decryption
FILE_COST = 5  # Cost for file-based decryption

description = "Decrypt SKS content with advanced encryption (costs 4-5 coins)"

# Config keys for decryption
config_keys = [
    "162exe235948e37ws6d057d9d85324e2",
    "dyv35182!",
    "dyv35224nossas!!",
    "662ede816988e58fb6d057d9d85605e0",
    "962exe865948e37ws6d057d4d85604e0",
    "175exe868648e37wb9x157d4l45604l0",
    "c7-YOcjyk1k",
    "Wasjdeijs@/ÇPãoOf231#$%¨&*()_qqu&iJo>ç",
    "Ed\x01",
    "fubvx788b46v",
    "fubgf777gf6",
    "cinbdf665$4",
    "furious0982",
    "error",
    "Jicv",
    "mtscrypt",
    "62756C6F6B",
    "rdovx202b46v",
    "xcode788b46z",
    "y$I@no5#lKuR7ZH#eAgORu6QnAF*vP0^JOTyB1ZQ&*w^RqpGkY",
    "kt",
    "fubvx788B4mev",
    "thirdy1996624",
    "bKps&92&",
    "waiting",
    "gggggg",
    "fuMnrztkzbQ",
    "A^ST^f6ASG6AS5asd",
    "cnt",
    "chaveKey",
    "Version6",
    "trfre699g79r",
    "chanika acid, gimsara htpcag!!",
    "xcode788b46z",
    "cigfhfghdf665557",
    "0x0",
    "2$dOxdIb6hUpzb*Y@B0Nj!T!E2A6DOLlwQQhs4RO6QpuZVfjGx",
    "W0RFRkFVTFRd",
    "Bgw34Nmk",
    "B1m93p$$9pZcL9yBs0b$jJwtPM5VG@Vg",
    "fubvx788b46vcatsn",
    "$$$@mfube11!!_$$))012b4u",
    "zbNkuNCGSLivpEuep3BcNA==",
    "175exe867948e37wb9d057d4k45604l0"
]

def aes_decrypt(data, key, iv):
    """Decrypt AES encrypted data"""
    aes_instance = AES.new(b64decode(key), AES.MODE_CBC, b64decode(iv))
    decrypted_data = aes_instance.decrypt(b64decode(data))
    return decrypted_data.decode('utf-8').rstrip('\x10')

def md5crypt(data):
    """Generate MD5 hash of data"""
    return hashlib.md5(data.encode()).hexdigest()

def clean_json_data(data):
    """Extract valid JSON from string"""
    start = data.find('{')
    end = data.rfind('}') + 1
    if start == -1 or end == -1:
        raise ValueError("Failed to locate JSON data")
    return data[start:end]

def decrypt_data(data, iv, version):
    """Try decryption with different keys"""
    for key in config_keys:
        try:
            aes_key = b64encode(md5crypt(key + " " + str(version)).encode()).decode()
            decrypted_data = aes_decrypt(data, aes_key, iv)
            return clean_json_data(decrypted_data)
        except Exception:
            continue
    raise Exception("No valid key found")

def format_output(data, indent=0):
    """Format decrypted data with proper indentation"""
    lines = []
    prefix = "  " * indent
    
    for key, value in data.items():
        if key == "message":
            continue
        if isinstance(value, dict):
            lines.append(f"{prefix}*{key}:*")
            lines.extend(format_output(value, indent + 1))
        elif isinstance(value, list):
            formatted_list = ", ".join(f"`{str(item)}`" for item in value)
            lines.append(f"{prefix}*{key}:* [{formatted_list}]")
        else:
            lines.append(f"{prefix}*{key}:* `{value}`")
    return lines

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the sks command"""
    try:
        # Get user information
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        user = db.get_user(user_id, username)

        # Check if there's a file attached
        is_file = update.message.document and update.message.document.file_name.endswith('.sks')
        cost = FILE_COST if is_file else TEXT_COST

        # Check if user has enough coins
        if user['coins'] < cost:
            await update.message.reply_text(
                f"❌ Insufficient coins! You need `{cost}` coins for this operation.\nYour balance: `{user['coins']}` coins",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if is_file:
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
                    "*🔐 SKS Decryption Service*\n\n"
                    "Usage:\n"
                    "1. Text command: `sks <encrypted_content>`\n"
                    "   Cost: `4 coins`\n\n"
                    "2. File upload: Send `.sks` file\n"
                    "   Cost: `5 coins`\n\n"
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
            f'SKS decryption ({("file" if is_file else "text")} mode)'
        )

        # Process the decryption
        try:
            content_json = json.loads(encrypted_content)
            data = content_json['d']
            version = content_json['v']
            iv = data.split(".")[1]
            encrypted_part = data.split(".")[0]

            decrypted_data = decrypt_data(encrypted_part, iv, version)
            json_data = json.loads(decrypted_data)

            # Format output with markdown
            formatted_lines = ["*🔓 Decrypted Content:*\n"]
            formatted_lines.extend(format_output(json_data))
            formatted_content = "\n".join(formatted_lines)

            # Send the formatted message
            await update.message.reply_text(formatted_content, parse_mode=ParseMode.MARKDOWN)

            # Save and send as a file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(formatted_content)
                temp_file_path = temp_file.name

            # Send the file
            with open(temp_file_path, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename='decrypted_sks.txt',
                    caption='🔓 Decrypted content saved in this file'
                )

            # Clean up
            os.unlink(temp_file_path)

            # Get updated user balance
            updated_user = db.get_user(user_id)

            # Send completion message with balance
            file_size_kb = len(formatted_content.encode('utf-8')) / 1024
            await update.message.reply_text(
                f"✅ Decryption complete!\n"
                f"Cost: `-{cost}` coins\n"
                f"File size: `{file_size_kb:.2f}` KB\n"
                f"Current balance: `{updated_user['coins']}` coins",
                parse_mode=ParseMode.MARKDOWN
            )

        except json.JSONDecodeError:
            await update.message.reply_text("❌ Invalid JSON format", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Decryption error: `{str(e)}`", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )