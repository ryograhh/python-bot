from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
import os
import ssl
import certifi
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://biaronab:Yg1cxmqdHZgkjywD@cluster0.vm9kj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

class MongoDB:
    def __init__(self):
        try:
            # Configure MongoDB client with SSL settings
            self.client = MongoClient(
                MONGO_URI,
                ssl=True,
                ssl_ca_certs=certifi.where(),
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
                w='majority'
            )
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            self.db = self.client[DB_NAME]
            self.users = self.db.users
            self.transactions = self.db.transactions
            
            # Create indexes
            self._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            raise

    def _create_indexes(self):
        """Create necessary indexes"""
        try:
            # Create indexes with background=True for better performance
            self.users.create_index('user_id', unique=True, background=True)
            self.users.create_index('username', background=True)
            self.transactions.create_index('user_id', background=True)
            self.transactions.create_index('created_at', background=True)
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
            logger.error(f"❌ Error getting/creating user: {str(e)}")
            raise

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
            logger.error(f"❌ Error updating user coins: {str(e)}")
            raise

    def update_last_daily(self, user_id: str):
        """Update user's last daily claim time"""
        try:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_daily': datetime.now()}}
            )
        except Exception as e:
            logger.error(f"❌ Error updating last daily: {str(e)}")
            raise

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
            logger.error(f"❌ Error adding transaction: {str(e)}")
            raise

    def get_transactions(self, user_id: str, limit: int = 5) -> list:
        """Get user's transaction history"""
        try:
            return list(self.transactions.find(
                {'user_id': user_id},
                {'_id': 0}
            ).sort('created_at', -1).limit(limit))
        except Exception as e:
            logger.error(f"❌ Error getting transactions: {str(e)}")
            raise

    def find_user_by_username(self, username: str) -> dict:
        """Find user by username (case insensitive)"""
        try:
            return self.users.find_one({
                'username': {'$regex': f'^{username}$', '$options': 'i'}
            })
        except Exception as e:
            logger.error(f"❌ Error finding user by username: {str(e)}")
            raise

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