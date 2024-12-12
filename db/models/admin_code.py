# db/models/admin_code.py
from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)

class AdminCodeModel:
    def __init__(self, db):
        self.admin_codes = db.admin_codes
        self.users = db.users

    def get_code_with_users(self, code: str) -> dict:
        """Get admin code with detailed user information"""
        try:
            code_data = self.admin_codes.find_one({'code': code}, {'_id': 0})
            if code_data and code_data.get('used_by'):
                user_details = []
                for user_id in code_data['used_by']:
                    user = self.users.find_one({'user_id': user_id}, {'_id': 0})
                    if user:
                        user_details.append({
                            'user_id': user_id,
                            'username': user.get('username', 'Unknown'),
                            'used_at': user.get('last_used')
                        })
                code_data['user_details'] = user_details
            return code_data
        except Exception as e:
            logger.error(f"Error getting code with users: {str(e)}")
            raise

    def use_admin_code(self, code: str, user_id: str) -> dict:
        """Use an admin code to get coins"""
        try:
            admin_code = self.admin_codes.find_one({'code': code.upper()})
            
            if not admin_code:
                return {'success': False, 'error': 'Invalid code'}
            
            max_uses = admin_code.get('max_uses', 1)
            used_by = admin_code.get('used_by', [])
            current_uses = len(used_by)
            
            if not admin_code.get('is_active', True):
                status = 'fully redeemed' if current_uses >= max_uses else 'expired'
                return {'success': False, 'error': f'Code has been {status}'}
            
            if current_uses >= max_uses:
                self.admin_codes.update_one(
                    {'_id': admin_code['_id']},
                    {'$set': {'status': 'fully_redeemed', 'is_active': False}}
                )
                return {'success': False, 'error': 'Code has reached maximum uses'}
            
            if user_id in used_by:
                return {'success': False, 'error': 'You have already used this code'}
            
            coins_amount = admin_code.get('coins', 0)
            uses_after = current_uses + 1
            new_status = 'fully_redeemed' if uses_after >= max_uses else 'active'
            new_is_active = uses_after < max_uses
            
            # Update user's coins first
            result = self.users.find_one_and_update(
                {'user_id': user_id},
                {'$inc': {'coins': coins_amount}},
                return_document=True
            )
            
            if not result:
                return {'success': False, 'error': 'Failed to update user coins'}
            
            # Update code usage
            self.admin_codes.update_one(
                {'_id': admin_code['_id']},
                {
                    '$push': {
                        'used_by': user_id,
                        'redemption_history': {
                            'user_id': user_id,
                            'redeemed_at': datetime.now()
                        }
                    },
                    '$set': {
                        'status': new_status,
                        'is_active': new_is_active,
                        'last_used': datetime.now()
                    }
                }
            )
            
            return {
                'success': True,
                'coins_added': coins_amount,
                'remaining_uses': max_uses - uses_after,
                'new_balance': result['coins']  # Include new balance in response
            }
                
        except Exception as e:
            logger.error(f"Error using admin code: {str(e)}")
            raise

    def create_admin_code(self, coins: int, description: str = "", max_uses: int = 1) -> dict:
        """Create a new admin code for coin distribution"""
        try:
            max_uses = max(1, int(max_uses))
            code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            
            admin_code = {
                'code': code,
                'coins': int(coins),
                'description': description,
                'created_at': datetime.now(),
                'used_by': [],
                'max_uses': max_uses,
                'is_active': True,
                'status': 'active'
            }
            
            result = self.admin_codes.insert_one(admin_code)
            created_code = self.admin_codes.find_one({'_id': result.inserted_id})
            
            if created_code:
                created_code['_id'] = str(created_code['_id'])
            return created_code
                
        except Exception as e:
            logger.error(f"Error creating admin code: {str(e)}")
            raise

    def get_admin_codes(self, include_inactive: bool = False) -> list:
        """Get list of admin codes with user details"""
        try:
            query = {} if include_inactive else {'is_active': True}
            codes = list(self.admin_codes.find(query, {'_id': 0}).sort('created_at', -1))
            
            for code in codes:
                uses = len(code.get('used_by', []))
                max_uses = code.get('max_uses', 1)
                
                if not code.get('is_active'):
                    code['status'] = 'fully_redeemed' if uses >= max_uses else 'expired'
                else:
                    code['status'] = 'active'
                    
                code['uses_remaining'] = max_uses - uses
                
                # Add user details
                user_details = []
                for user_id in code.get('used_by', []):
                    user = self.users.find_one({'user_id': user_id}, {'_id': 0})
                    if user:
                        user_details.append({
                            'user_id': user_id,
                            'username': user.get('username', 'Unknown')
                        })
                code['user_details'] = user_details
                
            return codes
                
        except Exception as e:
            logger.error(f"Error getting admin codes: {str(e)}")
            raise

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
            raise