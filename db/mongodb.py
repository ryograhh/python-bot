from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import ssl

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

class MongoDB:
    def __init__(self):
        try:
            # Configure MongoDB client with Railway-friendly settings
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                connect=True,
                retryWrites=True,
                tls=True,
                tlsAllowInvalidCertificates=True,
                tlsInsecure=True,
                directConnection=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            self.db = self.client[DB_NAME]
            self.users = self.db.users
            self.transactions = self.db.transactions
            
            # Create indexes
            self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            raise

    def _create_indexes(self):
        """Create necessary indexes"""
        try:
            self.users.create_index('user_id', unique=True)
            self.users.create_index('username')
            self.transactions.create_index([('user_id', 1), ('created_at', -1)])
            logger.info("✅ MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {str(e)}")
            raise

    def get_user(self, user_id: str, username: str = None) -> dict:
        """Get or create user"""
        try:
            user = self.users.find_one({'user_id': user_id})
            if not user:
                user = {
                    'user_id': user_id,
                    'username': username or 'Unknown',
                    'coins': 0,
                    'last_daily': None,
                    'created_at': datetime.now()
                }
                self.users.insert_one(user)
            return user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            # Attempt to reconnect
            self.client = MongoClient(MONGO_URI)
            return self.get_user(user_id, username)

    def update_user_coins(self, user_id: str, amount: int) -> int:
        """Update user's coin balance"""
        try:
            result = self.users.find_one_and_update(
                {'user_id': user_id},
                {'$inc': {'coins': amount}},
                return_document=True
            )
            return result['coins'] if result else None
        except Exception as e:
            logger.error(f"Error updating coins: {str(e)}")
            self.client = MongoClient(MONGO_URI)
            return self.update_user_coins(user_id, amount)

    def update_last_daily(self, user_id: str):
        """Update user's last daily claim time"""
        try:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_daily': datetime.now()}}
            )
        except Exception as e:
            logger.error(f"Error updating last daily: {str(e)}")
            self.client = MongoClient(MONGO_URI)
            self.update_last_daily(user_id)

    def add_transaction(self, user_id: str, amount: int, type_: str, description: str):
        """Add a transaction record"""
        try:
            transaction = {
                'user_id': user_id,
                'amount': amount,
                'type': type_,
                'description': description,
                'created_at': datetime.now()
            }
            self.transactions.insert_one(transaction)
        except Exception as e:
            logger.error(f"Error adding transaction: {str(e)}")
            self.client = MongoClient(MONGO_URI)
            self.add_transaction(user_id, amount, type_, description)

    def get_transactions(self, user_id: str, limit: int = 5) -> list:
        """Get user's transaction history"""
        try:
            return list(self.transactions.find(
                {'user_id': user_id},
                {'_id': 0}
            ).sort('created_at', -1).limit(limit))
        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            self.client = MongoClient(MONGO_URI)
            return self.get_transactions(user_id, limit)

    def find_user_by_username(self, username: str) -> dict:
        """Find user by username (case insensitive)"""
        try:
            return self.users.find_one({
                'username': {'$regex': f'^{username}$', '$options': 'i'}
            })
        except Exception as e:
            logger.error(f"Error finding user: {str(e)}")
            self.client = MongoClient(MONGO_URI)
            return self.find_user_by_username(username)

    def __del__(self):
        """Cleanup method to close MongoDB connection"""
        try:
            self.client.close()
        except:
            pass

# Create global database instance
try:
    db = MongoDB()
except Exception as e:
    logger.critical(f"❌ Failed to initialize MongoDB: {str(e)}")
    raise