from flask import Flask, render_template, jsonify, request
from threading import Thread
from api import setup_bot
from mongodb import db
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
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'Jubiar101')

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
        users = list(db.users.find({}, {'_id': 0}))
        return jsonify(format_json(users))
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/transactions')
def get_transactions():
    """API endpoint to get transactions"""
    try:
        transactions = list(db.transactions.find(
            {}, 
            {'_id': 0}
        ).sort('created_at', -1).limit(100))
        return jsonify(format_json(transactions))
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

        codes = list(db.admin_codes.find({}, {'_id': 0}).sort('created_at', -1))
        return jsonify(format_json(codes))
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

        created_code = db.create_admin_code(
            coins=int(data['coins']),
            description=data.get('description', '')
        )
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

        result = db.use_admin_code(code, user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error redeeming code: {str(e)}")
        return jsonify({'error': 'Failed to redeem code'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
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

        # Initialize MongoDB
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