# db/models/user.py
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserModel:
    def __init__(self, db):
        self.users = db.users
        self.transactions = db.transactions
        
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
            logger.error(f"Error updating coins: {str(e)}")
            raise

    def update_last_daily(self, user_id: str):
        """Update user's last daily claim time"""
        try:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_daily': datetime.now()}}
            )
        except Exception as e:
            logger.error(f"Error updating last daily: {str(e)}")
            raise

    def find_user_by_username(self, username: str) -> dict:
        """Find user by username (case insensitive)"""
        try:
            return self.users.find_one({
                'username': {'$regex': f'^{username}$', '$options': 'i'}
            })
        except Exception as e:
            logger.error(f"Error finding user: {str(e)}")
            raise