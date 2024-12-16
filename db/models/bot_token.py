from datetime import datetime
from pymongo.collection import Collection
from cryptography.fernet import Fernet
import bcrypt

class BotTokenModel:
    def __init__(self, db):
        self.collection: Collection = db.bot_tokens
        
    def create_bot(self, user_id: str, token: str, bot_name: str, encryption_key: bytes):
        """Create a new bot entry with encrypted token"""
        f = Fernet(encryption_key)
        encrypted_token = f.encrypt(token.encode())
        
        return self.collection.insert_one({
            'user_id': user_id,
            'bot_name': bot_name,
            'token': encrypted_token,
            'created_at': datetime.utcnow(),
            'is_active': True,
            'last_active': datetime.utcnow()
        })

    def get_user_bots(self, user_id: str, encryption_key: bytes):
        """Get all bots for a user with decrypted tokens"""
        f = Fernet(encryption_key)
        bots = list(self.collection.find({'user_id': user_id}))
        
        for bot in bots:
            bot['token'] = f.decrypt(bot['token']).decode()
        
        return bots

    def update_bot_status(self, bot_id: str, is_active: bool):
        """Update bot active status"""
        return self.collection.update_one(
            {'_id': bot_id},
            {
                '$set': {
                    'is_active': is_active,
                    'last_active': datetime.utcnow()
                }
            }
        )

class UserAuthModel:
    def __init__(self, db):
        self.collection: Collection = db.users_auth
        
    def create_user(self, username: str, password: str) -> dict:
        """Create a new user with hashed password"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        encryption_key = Fernet.generate_key()
        
        user = {
            'username': username,
            'password': hashed,
            'encryption_key': encryption_key,
            'created_at': datetime.utcnow()
        }
        
        self.collection.insert_one(user)
        return user

    def verify_user(self, username: str, password: str) -> dict:
        """Verify user credentials and return user data"""
        user = self.collection.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode(), user['password']):
            return user
        return None

    def get_encryption_key(self, username: str) -> bytes:
        """Get user's encryption key"""
        user = self.collection.find_one({'username': username})
        return user['encryption_key'] if user else None