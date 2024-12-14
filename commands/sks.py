from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from db.database import db
import json
import hashlib
from Crypto.Cipher import AES
from base64 import b64decode, b64encode
import os
import re

description = "Decrypt encrypted content (costs 4 coins for text, 5 coins for .sks files)"
admin_bot = True

# Configuration keys
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
    aes_instance = AES.new(b64decode(key), AES.MODE_CBC, b64decode(iv))
    decrypted_data = aes_instance.decrypt(b64decode(data))
    return decrypted_data.decode('utf-8').rstrip('\x10')

def md5crypt(data):
    return hashlib.md5(data.encode()).hexdigest()

def clean_json_data(data):
    start = data.find('{')
    end = data.rfind('}') + 1
    if start == -1 or end == -1:
        raise ValueError("Failed to locate JSON data")
    return data[start:end]

def decrypt_data(data, iv, version):
    for key in config_keys:
        try:
            aes_key = b64encode(md5crypt(key + " " + str(version)).encode()).decode()
            decrypted_data = aes_decrypt(data, aes_key, iv)
            return clean_json_data(decrypted_data)
        except Exception:
            continue
    raise Exception("No valid key found")

def format_output(data):
    lines = []
    for key, value in data.items():
        if key == "message":
            continue
        if isinstance(value, dict):
            lines.append(f"🔑 {key}:")
            lines.extend(format_output(value))
        elif isinstance(value, list):
            lines.append(f"🔑 {key}: [{', '.join(map(str, value))}]")
        else:
            lines.append(f"🔑 {key}: {value}")
    return lines

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        user = db.users.get_user(user_id, username)
        
        is_file = bool(update.message.document and update.message.document.file_name.endswith('.sks'))
        coin_cost = 5 if is_file else 4

        if user['coins'] < coin_cost:
            await update.message.reply_text(
                f"❌ Insufficient coins! Need {coin_cost} coins\n"
                f"Current balance: {user['coins']} coins"
            )
            return

        try:
            if is_file:
                file = await update.message.document.get_file()
                file_content = await file.download_as_bytearray()
                encrypted_content = file_content.decode('utf-8')
            else:
                if len(update.message.text.split()) < 2:
                    await update.message.reply_text("❌ Please provide encrypted content!")
                    return
                encrypted_content = update.message.text.split(" ", 1)[1]

            content_json = json.loads(encrypted_content)
            data = content_json['d']
            version = content_json['v']
            iv = data.split(".")[1]
            encrypted_part = data.split(".")[0]

            decrypted_data = decrypt_data(encrypted_part, iv, version)
            json_data = json.loads(decrypted_data)

            # Deduct coins after successful decryption
            db.users.update_user_coins(user_id, -coin_cost)
            db.transactions.add_transaction(
                user_id=user_id,
                amount=-coin_cost,
                type_='service',
                description=f'SKS decryption ({("file" if is_file else "text")} mode)'
            )

            # Format content
            header = [f"🎉 *Decrypted Content:* \\(\\-{coin_cost} coins\\)\n```"]
            content_lines = format_output(json_data)
            formatted_content = "\n".join(header + content_lines + ["```"])

            # Send formatted text with markdown
            await update.message.reply_text(
                formatted_content,
                parse_mode=ParseMode.MARKDOWN_V2
            )

            # Create and send file attachment
            temp_file_path = os.path.join(os.path.dirname(__file__), "decrypted.txt")
            with open(temp_file_path, "w", encoding="utf-8") as file:
                # Remove markdown for file content
                plain_content = re.sub(r'[`*_~]', '', formatted_content)
                plain_content = re.sub(r'\\(.)', r'\1', plain_content)
                file.write(plain_content)

            # Get updated balance for the caption
            updated_user = db.users.get_user(user_id)
            caption = (
                f"💰 Current Balance: {updated_user['coins']} coins\n"
                f"💸 Cost: {coin_cost} coins\n"
                f"✨ Thank you for using our service!"
            )

            with open(temp_file_path, "rb") as file:
                await update.message.reply_document(
                    document=file,
                    filename="decrypted.txt",
                    caption=caption
                )

            os.remove(temp_file_path)

        except json.JSONDecodeError:
            await update.message.reply_text(
                "❌ Invalid encrypted content format\\. No coins were deducted\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Decryption failed: {str(e)}\\. No coins were deducted\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\\. No coins were deducted\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )