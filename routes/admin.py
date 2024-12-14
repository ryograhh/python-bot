from flask import jsonify, request, render_template
from datetime import datetime
import random
from db.database import db
import logging
import json

logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def init_admin_routes(app):
    @app.route('/api/admin/codes/create', methods=['POST'])
    def create_admin_code():
        try:
            data = request.get_json()
            if int(data.get('coins', 0)) < 1:
                return jsonify({'error': 'Coins amount must be greater than 0'}), 400

            code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            admin_code = {
                'code': code,
                'coins': int(data.get('coins', 0)),
                'description': data.get('description', ''),
                'created_at': datetime.now(),
                'used_by': [],
                'max_uses': int(data.get('max_uses', 1)),
                'is_active': True,
                'status': 'active'
            }
            
            result = db.admin_codes.admin_codes.insert_one(admin_code)
            created_code = db.admin_codes.admin_codes.find_one({'_id': result.inserted_id})
            created_code.pop('_id', None)
            return jsonify(created_code)
        except Exception as e:
            logger.error(f"Error creating admin code: {str(e)}")
            return jsonify({'error': 'Failed to create admin code'}), 500

    @app.route('/api/admin/codes/<code_id>', methods=['DELETE'])
    def delete_code(code_id):
        try:
            # First check if the code exists and is eligible for deletion
            code = db.admin_codes.admin_codes.find_one({'code': code_id})
            if not code:
                return jsonify({'error': 'Code not found'}), 404

            # Check if code is fully redeemed (additional safety check)
            uses = len(code.get('used_by', []))
            max_uses = code.get('max_uses', 1)
            if code.get('is_active') or (uses < max_uses):
                return jsonify({'error': 'Only fully redeemed codes can be deleted'}), 400

            # Delete the code
            result = db.admin_codes.admin_codes.delete_one({'code': code_id})
            
            if result.deleted_count == 1:
                return jsonify({'success': True, 'message': 'Code deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete code'}), 500
                
        except Exception as e:
            logger.error(f"Error deleting admin code {code_id}: {str(e)}")
            return jsonify({'error': 'Failed to delete admin code'}), 500

    @app.route('/admin/codes')
    def admin_codes():
        try:
            codes = list(db.admin_codes.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
            for code in codes:
                uses = len(code.get('used_by', []))
                max_uses = code.get('max_uses', 1)
                code['status'] = 'fully_redeemed' if not code.get('is_active') and uses >= max_uses else 'expired' if not code.get('is_active') else 'active'
                
                if code.get('used_by'):
                    code['user_details'] = []
                    for user_id in code['used_by']:
                        user = db.users.users.find_one({'user_id': user_id}, {'_id': 0, 'user_id': 1, 'username': 1})
                        if user:
                            code['user_details'].append({
                                'user_id': user_id,
                                'username': user.get('username', 'Unknown'),
                                'used_at': code.get('last_used')
                            })
            
            # Convert codes to JSON using the custom encoder
            admin_codes_json = json.dumps(codes, cls=JSONEncoder)
            return render_template('admin_codes.html', admin_codes_json=admin_codes_json)
        except Exception as e:
            logger.error(f"Error rendering admin codes template: {str(e)}")
            return render_template('error.html', error="Unable to load admin codes"), 500

    @app.route('/api/admin/codes', methods=['GET'])
    def get_admin_codes():
        try:
            codes = list(db.admin_codes.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
            for code in codes:
                uses = len(code.get('used_by', []))
                max_uses = code.get('max_uses', 1)
                code['status'] = 'fully_redeemed' if not code.get('is_active') and uses >= max_uses else 'expired' if not code.get('is_active') else 'active'
                
                if code.get('used_by'):
                    code['user_details'] = [{
                        'user_id': user_id,
                        'username': db.users.users.find_one({'user_id': user_id}, {'username': 1}).get('username', 'Unknown'),
                        'used_at': code.get('last_used')
                    } for user_id in code['used_by']]
                    
            return jsonify(codes)
        except Exception as e:
            logger.error(f"Error getting admin codes: {str(e)}")
            return jsonify({'error': 'Failed to fetch admin codes'}), 500