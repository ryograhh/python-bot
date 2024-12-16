# db/database.py
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from cryptography.fernet import Fernet
import bcrypt
from bson import ObjectId

logger = logging.getLogger(__name__)

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

    def get_bot(self, bot_id: ObjectId, user_id: str):
        """Get a specific bot by ID and user_id"""
        bot = self.collection.find_one({
            '_id': bot_id,
            'user_id': user_id
        })
        
        if bot:
            # Get encryption key for the user
            encryption_key = UserAuthModel(self.collection.database).get_encryption_key(user_id)
            if encryption_key:
                f = Fernet(encryption_key)
                bot['token'] = f.decrypt(bot['token']).decode()
        
        return bot

    def update_bot_status(self, bot_id: ObjectId, is_active: bool):
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

    def delete_bot(self, bot_id: ObjectId, user_id: str):
        """Delete a bot"""
        return self.collection.delete_one({
            '_id': bot_id,
            'user_id': user_id
        })

class UserAuthModel:
    def __init__(self, db):
        self.collection: Collection = db.users_auth
        
    def create_user(self, username: str, password: str) -> dict:
        """Create a new user with hashed password"""
        # Check if username already exists
        if self.collection.find_one({'username': username}):
            raise ValueError("Username already exists")
            
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        encryption_key = Fernet.generate_key()
        
        user = {
            'username': username,
            'password': hashed,
            'encryption_key': encryption_key,
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        
        self.collection.insert_one(user)
        return user

    def verify_user(self, username: str, password: str) -> dict:
        """Verify user credentials and return user data"""
        user = self.collection.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode(), user['password']):
            # Update last login time
            self.collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
            return user
        return None

    def get_encryption_key(self, username: str) -> bytes:
        """Get user's encryption key"""
        user = self.collection.find_one({'username': username})
        return user['encryption_key'] if user else None

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user's password"""
        user = self.verify_user(username, old_password)
        if not user:
            return False
            
        salt = bcrypt.gensalt()
        new_hashed = bcrypt.hashpw(new_password.encode(), salt)
        
        result = self.collection.update_one(
            {'_id': user['_id']},
            {'$set': {'password': new_hashed}}
        )
        return result.modified_count > 0

class Database:
    def __init__(self):
        try:
            # Default to localhost if no URI is provided
            mongo_uri = 'mongodb+srv://biaronab:Yg1cxmqdHZgkjywD@cluster0.vm9kj.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true'
            self.client = MongoClient(mongo_uri)
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            db = self.client['bot_manager']
            self._create_indexes(db)
            
            # Initialize models
            self.bot_tokens = BotTokenModel(db)
            self.users_auth = UserAuthModel(db)
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            raise

    def _create_indexes(self, db):
        """Create necessary indexes"""
        try:
            # User authentication indexes
            db.users_auth.create_index('username', unique=True)
            db.users_auth.create_index('created_at')
            
            # Bot token indexes
            db.bot_tokens.create_index('user_id')
            db.bot_tokens.create_index([('user_id', 1), ('bot_name', 1)], unique=True)
            db.bot_tokens.create_index('created_at')
            db.bot_tokens.create_index('last_active')
            
            logger.info("✅ MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"❌ MongoDB Error creating indexes: {str(e)}")
            raise

    def get_bot_stats(self):
        """Get general statistics about bots"""
        try:
            stats = {
                'total_users': self.client['bot_manager'].users_auth.count_documents({}),
                'total_bots': self.client['bot_manager'].bot_tokens.count_documents({}),
                'active_bots': self.client['bot_manager'].bot_tokens.count_documents({'is_active': True}),
                'total_messages_processed': 0  # You can add message tracking if needed
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return None

    def __del__(self):
        """Cleanup method to close database connection"""
        try:
            self.client.close()
        except:
            pass

# Create global database instance
try:
    db = Database()
except Exception as e:
    logger.critical(f"❌ Failed to initialize database: {str(e)}")
    raise