from flask import Flask, render_template, jsonify, request
from threading import Thread
from api import setup_bot
from db.database import db  # Updated import for new database structure
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import json
from bson import json_util
import os
import sys
import logging
from datetime import datetime
import random
from flask_cors import CORS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Flask
app = Flask(__name__)
CORS(app)

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

def serialize_datetime(obj):
    """Helper function to serialize datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def format_json(data):
    """Format MongoDB data for JSON response"""
    if isinstance(data, list):
        return [
            {k: serialize_datetime(v) for k, v in item.items()}
            for item in data
        ]
    elif isinstance(data, dict):
        return {k: serialize_datetime(v) for k, v in data.items()}
    return data

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    
@app.route('/')
def home():
    """Render the dashboard template"""
    try:
        users = list(db.users.users.find({}, {'_id': 0}))
        transactions = list(db.transactions.transactions.find({}, {'_id': 0}).sort('created_at', -1).limit(100))
        return render_template('index.html', 
                             users=format_json(users),
                             transactions=format_json(transactions))
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return render_template('error.html', error="Unable to load dashboard"), 500

@app.route('/api/users')
def get_users():
    """API endpoint to get all users"""
    try:
        users = list(db.users.users.find({}, {'_id': 0}))
        return jsonify(format_json(users))
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/transactions')
def get_transactions():
    """API endpoint to get transactions"""
    try:
        transactions = list(db.transactions.transactions.find(
            {}, 
            {'_id': 0}
        ).sort('created_at', -1).limit(100))
        return jsonify(format_json(transactions))
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

# Admin Code Routes
@app.route('/api/admin/codes/create', methods=['POST'])
def create_admin_code():
    """Create a new admin code"""
    try:
        data = request.get_json()
        coins = int(data.get('coins', 0))
        description = data.get('description', '')
        max_uses = int(data.get('max_uses', 1))
        
        if coins < 1:
            return jsonify({'error': 'Coins amount must be greater than 0'}), 400

        # Generate a random 8-character code
        code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        
        admin_code = {
            'code': code,
            'coins': coins,
            'description': description,
            'created_at': datetime.now(),
            'used_by': [],
            'max_uses': max_uses,
            'is_active': True,
            'status': 'active'
        }
        
        # Insert the code
        result = db.admin_codes.admin_codes.insert_one(admin_code)
        created_code = db.admin_codes.admin_codes.find_one({'_id': result.inserted_id})
        
        if created_code:
            created_code.pop('_id', None)  # Remove _id for JSON serialization
            return jsonify(format_json(created_code))
        return jsonify({'error': 'Failed to create code'}), 500
            
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error creating admin code: {str(e)}")
        return jsonify({'error': 'Failed to create admin code'}), 500

@app.route('/admin/codes')
def admin_codes():
    """Render the admin codes page with proper JSON data"""
    try:
        codes = list(db.admin_codes.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
        
        # Format codes and their status
        for code in codes:
            if not code.get('is_active'):
                code['status'] = 'fully_redeemed' if len(code.get('used_by', [])) >= code.get('max_uses', 1) else 'expired'
            else:
                code['status'] = 'active'
            
            # Add user details if available
            if code.get('used_by'):
                user_details = []
                for user_id in code['used_by']:
                    user = db.users.users.find_one({'user_id': user_id}, {'_id': 0, 'user_id': 1, 'username': 1})
                    if user:
                        user_details.append({
                            'user_id': user_id,
                            'username': user.get('username', 'Unknown'),
                            'used_at': code.get('last_used')
                        })
                code['user_details'] = user_details
                
        # Format and serialize to JSON using custom encoder
        formatted_codes = format_json(codes)
        admin_codes_json = json.dumps(formatted_codes, cls=JSONEncoder)
        
        return render_template('admin_codes.html', admin_codes_json=admin_codes_json)
    except Exception as e:
        logger.error(f"Error rendering admin codes template: {str(e)}")
        return render_template('error.html', error="Unable to load admin codes"), 500

@app.route('/api/admin/codes', methods=['GET'])
def get_admin_codes():
    """Get all admin codes"""
    try:
        codes = list(db.admin_codes.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
        
        # Add computed status for each code
        for code in codes:
            uses = len(code.get('used_by', []))
            max_uses = code.get('max_uses', 1)
            
            if not code.get('is_active'):
                code['status'] = 'fully_redeemed' if uses >= max_uses else 'expired'
            else:
                code['status'] = 'active'
            
            # Add user details
            if code.get('used_by'):
                user_details = []
                for user_id in code['used_by']:
                    user = db.users.users.find_one({'user_id': user_id}, {'_id': 0, 'user_id': 1, 'username': 1})
                    if user:
                        user_details.append({
                            'user_id': user_id,
                            'username': user.get('username', 'Unknown'),
                            'used_at': code.get('last_used')
                        })
                code['user_details'] = user_details
                
        return jsonify(format_json(codes))
    except Exception as e:
        logger.error(f"Error getting admin codes: {str(e)}")
        return jsonify({'error': 'Failed to fetch admin codes'}), 500

@app.route('/api/redeem/<code>')
def redeem_code(code):
    """Redeem an admin code"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        # Find the code
        admin_code = db.admin_codes.admin_codes.find_one({'code': code.upper()})
        if not admin_code:
            return jsonify({'success': False, 'error': 'Invalid code'})

        # Process redemption
        result = db.admin_codes.use_admin_code(code, user_id)
        
        if result['success']:
            # Add transaction record
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

@app.route('/api/admin/codes/<code_id>', methods=['DELETE'])
def delete_admin_code(code_id):
    """Delete an admin code"""
    try:
        result = db.admin_codes.admin_codes.find_one_and_delete({
            'code': code_id,
            'is_active': False,
            'status': 'fully_redeemed'
        })
        
        if result:
            return jsonify({'success': True}), 200
        return jsonify({'error': 'Code not found or not eligible for deletion'}), 404
    except Exception as e:
        logger.error(f"Error deleting admin code: {str(e)}")
        return jsonify({'error': 'Failed to delete admin code'}), 500

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        total_users = db.users.users.count_documents({})
        total_transactions = db.transactions.transactions.count_documents({})
        total_coins = sum(user.get('coins', 0) for user in db.users.users.find({}, {'coins': 1}))
        active_codes = db.admin_codes.admin_codes.count_documents({'is_active': True})

        return jsonify({
            'total_users': total_users,
            'total_transactions': total_transactions,
            'total_coins': total_coins,
            'active_codes': active_codes,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': 'Failed to fetch stats'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        db.client.admin.command('ping')
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def run_flask():
    """Run Flask server with error handling"""
    try:
        app.run(
            host='0.0.0.0',
            port=3306,
            use_reloader=False,
            debug=False
        )
    except Exception as e:
        logger.error(f"Flask server error: {str(e)}")
        sys.exit(1)

def run_bot():
    """Run Telegram bot with error handling"""
    try:
        setup_bot()
    except Exception as e:
        logger.error(f"Telegram bot error: {str(e)}")
        sys.exit(1)

def main():
    try:
        # Verify environment variables
        if not MONGO_URI:
            raise ValueError("MONGO_URI environment variable is not set")

        # Initialize MongoDB connection
        db.client.admin.command('ping')
        logger.info("🚀 MongoDB connection successful")

        logger.info("🚀 Starting server...")

        # Start Flask in a separate thread
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Run the bot in the main thread
        run_bot()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()