from flask import jsonify, request
from datetime import datetime
from db.database import db
import logging

logger = logging.getLogger(__name__)

def register_api_routes(app):
    @app.route('/api/users')
    def get_users():
        try:
            users = list(db.users.users.find({}, {'_id': 0}))
            return jsonify(users)
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return jsonify({'error': 'Failed to fetch users'}), 500

    @app.route('/api/transactions')
    def get_transactions():
        try:
            transactions = list(db.transactions.transactions.find(
                {}, {'_id': 0}
            ).sort('created_at', -1).limit(100))
            return jsonify(transactions)
        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            return jsonify({'error': 'Failed to fetch transactions'}), 500

    @app.route('/api/redeem/<code>')
    def redeem_code(code):
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'User ID is required'}), 400

            admin_code = db.admin_codes.admin_codes.find_one({'code': code.upper()})
            if not admin_code:
                return jsonify({'success': False, 'error': 'Invalid code'})

            result = db.admin_codes.use_admin_code(code, user_id)
            if result['success']:
                db.transactions.add_transaction(
                    user_id=user_id,
                    amount=result['coins_added'],
                    type_='admin_code',
                    description=f"Redeemed code: {code}"
                )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error redeeming code: {str(e)}")
            return jsonify({'error': 'Failed to redeem code'}), 500