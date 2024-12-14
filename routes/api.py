from flask import jsonify, request
from datetime import datetime
from db.database import db
import logging

logger = logging.getLogger(__name__)

def register_api_routes(app):
    @app.route('/api/users')
    def get_users():
        try:
            users = list(db.users.users.find(
                {}, 
                {
                    '_id': 0,
                    'user_id': 1,
                    'username': 1,
                    'coins': 1,
                    'last_daily': 1
                }
            ))

            # Clean and validate user data
            for user in users:
                if 'coins' in user:
                    user['coins'] = float(user.get('coins', 0))
                if 'last_daily' in user and isinstance(user['last_daily'], datetime):
                    user['last_daily'] = user['last_daily'].isoformat()

            return jsonify(users)
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return jsonify({'error': 'Failed to fetch users'}), 500

    @app.route('/api/transactions')
    def get_transactions():
        try:
            # Get transactions with proper sorting
            transactions = list(db.transactions.transactions.find(
                {}, 
                {
                    '_id': 0,
                    'user_id': 1,
                    'amount': 1,
                    'type': 1,
                    'description': 1,
                    'created_at': 1
                }
            ).sort('created_at', -1).limit(100))

            # Clean and validate transaction data
            cleaned_transactions = []
            for tx in transactions:
                if not all(key in tx for key in ['user_id', 'amount', 'type']):
                    continue
                
                # Ensure amount is a number
                try:
                    tx['amount'] = float(tx['amount'])
                except (TypeError, ValueError):
                    continue

                # Format created_at date
                if 'created_at' in tx and isinstance(tx['created_at'], datetime):
                    tx['created_at'] = tx['created_at'].isoformat()

                cleaned_transactions.append(tx)

            return jsonify(cleaned_transactions)
        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            return jsonify({'error': 'Failed to fetch transactions'}), 500

    @app.route('/api/redeem/<code>')
    def redeem_code(code):
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'User ID is required'}), 400

            # Validate code exists
            admin_code = db.admin_codes.admin_codes.find_one({'code': code.upper()})
            if not admin_code:
                return jsonify({'success': False, 'error': 'Invalid code'})

            # Try to use the code
            result = db.admin_codes.use_admin_code(code, user_id)
            if result['success']:
                try:
                    db.transactions.add_transaction(
                        user_id=user_id,
                        amount=result['coins_added'],
                        type_='admin_code',
                        description=f"Redeemed code: {code}"
                    )
                except Exception as e:
                    logger.error(f"Error adding transaction record: {str(e)}")
                    # Continue since code was already used

            return jsonify(result)
        except Exception as e:
            logger.error(f"Error redeeming code: {str(e)}")
            return jsonify({'error': 'Failed to redeem code'}), 500