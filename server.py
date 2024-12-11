from flask import Flask, render_template, jsonify, request
from threading import Thread
from api import setup_bot
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import json
from bson import json_util
import os
import sys
import logging
from datetime import datetime
from flask_cors import CORS
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO
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
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'Jubiar101')  # Add this to your .env file

def get_db():
    """Get MongoDB client and database"""
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryWrites=True,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        db = client[DB_NAME]
        # Test connection
        client.admin.command('ping')
        return client, db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

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

# Main Routes
@app.route('/')
def home():
    """Render the dashboard template"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return render_template('error.html', error="Unable to load dashboard"), 500

@app.route('/graph')
def graph():
    """Render the graph analytics page"""
    try:
        return render_template('graph.html')
    except Exception as e:
        logger.error(f"Error rendering graph template: {str(e)}")
        return render_template('error.html', error="Unable to load graph"), 500

@app.route('/admin/codes')
def admin_codes():
    """Render the admin codes page"""
    try:
        return render_template('admin_codes.html')
    except Exception as e:
        logger.error(f"Error rendering admin codes template: {str(e)}")
        return render_template('error.html', error="Unable to load admin codes"), 500

# API Routes
@app.route('/api/users')
def get_users():
    """API endpoint to get all users"""
    try:
        client, db = get_db()
        users = list(db.users.find({}, {'_id': 0}))
        client.close()
        
        formatted_users = format_json(users)
        return jsonify(formatted_users)
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/transactions')
def get_transactions():
    """API endpoint to get transactions"""
    try:
        client, db = get_db()
        transactions = list(db.transactions.find(
            {}, 
            {'_id': 0}
        ).sort('created_at', -1).limit(100))
        client.close()
        
        formatted_transactions = format_json(transactions)
        return jsonify(formatted_transactions)
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

# Admin Code Routes
@app.route('/api/admin/codes', methods=['GET'])
def get_admin_codes():
    """Get all admin codes"""
    try:
        # Verify admin token
        token = request.headers.get('Authorization')
        if token != f"Bearer {ADMIN_TOKEN}":
            return jsonify({'error': 'Unauthorized'}), 401

        client, db = get_db()
        codes = list(db.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
        client.close()
        
        formatted_codes = format_json(codes)
        return jsonify(formatted_codes)
    except Exception as e:
        logger.error(f"Error getting admin codes: {str(e)}")
        return jsonify({'error': 'Failed to fetch admin codes'}), 500

@app.route('/api/admin/codes/create', methods=['POST'])
def create_admin_code():
    """Create a new admin code"""
    try:
        # Verify admin token
        token = request.headers.get('Authorization')
        if token != f"Bearer {ADMIN_TOKEN}":
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        if not data or 'coins' not in data:
            return jsonify({'error': 'Invalid request data'}), 400

        client, db = get_db()
        new_code = db.admin_codes.insert_one({
            'code': ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8)),
            'coins': int(data['coins']),
            'description': data.get('description', ''),
            'created_at': datetime.now(),
            'used_by': [],
            'is_active': True
        })
        
        created_code = db.admin_codes.find_one({'_id': new_code.inserted_id}, {'_id': 0})
        client.close()
        
        return jsonify(format_json(created_code))
    except Exception as e:
        logger.error(f"Error creating admin code: {str(e)}")
        return jsonify({'error': 'Failed to create admin code'}), 500

@app.route('/api/redeem/<code>')
def redeem_code(code):
    """Redeem an admin code"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        client, db = get_db()
        
        # Find the code
        admin_code = db.admin_codes.find_one({
            'code': code.upper(),
            'is_active': True
        })

        if not admin_code:
            return jsonify({'error': 'Invalid or expired code'}), 404

        # Check if user has already used this code
        if user_id in admin_code['used_by']:
            return jsonify({'error': 'Code already used'}), 400

        # Update user's coins
        result = db.users.find_one_and_update(
            {'user_id': user_id},
            {'$inc': {'coins': admin_code['coins']}},
            return_document=True
        )

        if not result:
            return jsonify({'error': 'User not found'}), 404

        # Mark code as used
        db.admin_codes.update_one(
            {'_id': admin_code['_id']},
            {'$push': {'used_by': user_id}}
        )

        # Add transaction record
        db.transactions.insert_one({
            'user_id': user_id,
            'amount': admin_code['coins'],
            'type': 'admin_code',
            'description': f"Redeemed code: {code}",
            'created_at': datetime.now()
        })

        client.close()
        
        return jsonify({
            'success': True,
            'coins_added': admin_code['coins'],
            'total_coins': result['coins']
        })
    except Exception as e:
        logger.error(f"Error redeeming code: {str(e)}")
        return jsonify({'error': 'Failed to redeem code'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        client, _ = get_db()
        client.admin.command('ping')
        client.close()
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
            debug=False  # Changed from True to False
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
        
        # Initialize MongoDB
        client, _ = get_db()
        client.admin.command('ping')
        client.close()
        
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