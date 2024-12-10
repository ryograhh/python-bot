from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://biaronab:Yg1cxmqdHZgkjywD@cluster0.vm9kj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.users = self.db.users
        self.transactions = self.db.transactions
        
        # Create indexes
        self.users.create_index('user_id', unique=True)
        self.users.create_index('username')
        self.transactions.create_index('user_id')
        self.transactions.create_index('created_at')

    def get_user(self, user_id: str, username: str = None):
        """Get or create user"""
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

    def update_user_coins(self, user_id: str, amount: int):
        """Update user's coin balance"""
        result = self.users.find_one_and_update(
            {'user_id': user_id},
            {'$inc': {'coins': amount}},
            return_document=True
        )
        return result['coins'] if result else None

    def update_last_daily(self, user_id: str):
        """Update user's last daily claim time"""
        self.users.update_one(
            {'user_id': user_id},
            {'$set': {'last_daily': datetime.now()}}
        )

    def add_transaction(self, user_id: str, amount: int, type_: str, description: str):
        """Add a transaction record"""
        transaction = {
            'user_id': user_id,
            'amount': amount,
            'type': type_,
            'description': description,
            'created_at': datetime.now()
        }
        self.transactions.insert_one(transaction)

    def get_transactions(self, user_id: str, limit: int = 5):
        """Get user's transaction history"""
        return list(self.transactions.find(
            {'user_id': user_id},
            {'_id': 0}  # Exclude MongoDB _id field
        ).sort('created_at', -1).limit(limit))

    def find_user_by_username(self, username: str):
        """Find user by username (case insensitive)"""
        return self.users.find_one({
            'username': {'$regex': f'^{username}$', '$options': 'i'}
        })

# Create global database instance
db = MongoDB()