from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import random
from bson import ObjectId

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
            # MongoDB connection configuration
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                retryWrites=True,
                tls=True,
                tlsAllowInvalidCertificates=True
            )
            
            # Test the connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            # Get the database and collections
            self.db = self.client[DB_NAME]
            self.users = self.db.users
            self.transactions = self.db.transactions
            self.admin_codes = self.db.admin_codes
            
            # Create necessary indexes
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
            self.admin_codes.create_index('code', unique=True)
            self.admin_codes.create_index('created_at')
            self.admin_codes.create_index('used_by')
            logger.info("✅ MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {str(e)}")
            raise

    def create_admin_code(self, coins: int, description: str = "", max_uses: int = 1) -> dict:
        """Create a new admin code for coin distribution"""
        try:
            # Ensure max_uses is at least 1
            max_uses = max(1, int(max_uses))
            
            # Generate a random 8-character code
            code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            
            admin_code = {
                'code': code,
                'coins': int(coins),
                'description': description,
                'created_at': datetime.now(),
                'used_by': [],  # List of user_ids who have used this code
                'max_uses': max_uses,  # Maximum number of times this code can be used
                'is_active': True,
                'status': 'active'  # active, expired, or fully_redeemed
            }
            
            # Insert the code
            result = self.admin_codes.insert_one(admin_code)
            
            # Get the complete document back
            created_code = self.admin_codes.find_one({'_id': result.inserted_id})
            
            # Convert ObjectId to string for JSON serialization
            if created_code:
                created_code['_id'] = str(created_code['_id'])
                
            return created_code
                
        except Exception as e:
            logger.error(f"Error creating admin code: {str(e)}")
            self.__init__()
            return self.create_admin_code(coins, description, max_uses)

    def use_admin_code(self, code: str, user_id: str) -> dict:
        """Use an admin code to get coins"""
        try:
            # Find the code and verify it's active
            admin_code = self.admin_codes.find_one({
                'code': code.upper()
            })
            
            if not admin_code:
                return {'success': False, 'error': 'Invalid code'}
            
            # Ensure max_uses exists
            max_uses = admin_code.get('max_uses', 1)  # Default to 1 if not set
            used_by = admin_code.get('used_by', [])
            current_uses = len(used_by)
            
            # Check if code is active
            if not admin_code.get('is_active', True):
                status = 'fully redeemed' if current_uses >= max_uses else 'expired'
                return {'success': False, 'error': f'Code has been {status}'}
            
            # Check if code has reached max uses
            if current_uses >= max_uses:
                # Update status to fully redeemed
                self.admin_codes.update_one(
                    {'_id': admin_code['_id']},
                    {
                        '$set': {
                            'status': 'fully_redeemed',
                            'is_active': False
                        }
                    }
                )
                return {'success': False, 'error': 'Code has reached maximum uses'}
            
            # Check if user has already used this code
            if user_id in used_by:
                return {'success': False, 'error': 'You have already used this code'}
            
            # Update user's coins
            coins_amount = admin_code.get('coins', 0)
            current_coins = self.update_user_coins(user_id, coins_amount)
            
            # Calculate new status
            uses_after = current_uses + 1
            new_status = 'fully_redeemed' if uses_after >= max_uses else 'active'
            new_is_active = uses_after < max_uses
            
            # Mark code as used by this user
            update_result = self.admin_codes.update_one(
                {'_id': admin_code['_id']},
                {
                    '$push': {'used_by': user_id},
                    '$set': {
                        'status': new_status,
                        'is_active': new_is_active,
                        'last_used': datetime.now()
                    }
                }
            )
            
            # Add transaction record
            self.add_transaction(
                user_id=user_id,
                amount=coins_amount,
                type_='admin_code',
                description=f"Redeemed code: {code}"
            )
            
            return {
                'success': True,
                'coins_added': coins_amount,
                'total_coins': current_coins,
                'remaining_uses': max_uses - uses_after
            }
                
        except Exception as e:
            logger.error(f"Error using admin code: {str(e)}")
            self.__init__()
            return self.use_admin_code(code, user_id)

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
            self.__init__()
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
            self.__init__()
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
            self.__init__()
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
            self.__init__()
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
            self.__init__()
            return self.get_transactions(user_id, limit)

    def find_user_by_username(self, username: str) -> dict:
        """Find user by username (case insensitive)"""
        try:
            return self.users.find_one({
                'username': {'$regex': f'^{username}$', '$options': 'i'}
            })
        except Exception as e:
            logger.error(f"Error finding user: {str(e)}")
            self.__init__()
            return self.find_user_by_username(username)

    def get_admin_codes(self, include_inactive: bool = False) -> list:
        """Get list of admin codes"""
        try:
            query = {} if include_inactive else {'is_active': True}
            codes = list(self.admin_codes.find(
                query,
                {'_id': 0}
            ).sort('created_at', -1))
            
            # Add computed status for each code
            for code in codes:
                uses = len(code.get('used_by', []))
                max_uses = code.get('max_uses', 1)
                
                if not code.get('is_active'):
                    code['status'] = 'fully_redeemed' if uses >= max_uses else 'expired'
                else:
                    code['status'] = 'active'
                    
                code['uses_remaining'] = max_uses - uses
                
            return codes
                
        except Exception as e:
            logger.error(f"Error getting admin codes: {str(e)}")
            self.__init__()
            return self.get_admin_codes(include_inactive)

    def delete_admin_code(self, code: str) -> bool:
        """Delete an admin code that is fully redeemed"""
        try:
            result = self.admin_codes.delete_one({
                'code': code,
                'is_active': False,
                'status': 'fully_redeemed'
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting admin code: {str(e)}")
            self.__init__()
            return self.delete_admin_code(code)

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