from flask import Flask, render_template, jsonify
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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Flask
app = Flask(__name__)
CORS(app)  # Enable CORS

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

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

@app.route('/')
def home():
    """Render the dashboard template"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return "Error loading dashboard", 500

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

def init_mongodb():
    """Initialize MongoDB connection and create indexes"""
    try:
        client, db = get_db()
        
        # Create collections if they don't exist
        if 'users' not in db.list_collection_names():
            db.create_collection('users')
        if 'transactions' not in db.list_collection_names():
            db.create_collection('transactions')
        
        # Create indexes
        db.users.create_index('user_id', unique=True)
        db.users.create_index('username')
        db.transactions.create_index([('user_id', 1), ('created_at', -1)])
        
        client.close()
        logger.info("✅ MongoDB initialization successful")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB initialization failed: {str(e)}")
        return False

def run_flask():
    """Run Flask server with error handling"""
    try:
        app.run(
            host='0.0.0.0',
            port=3306,
            use_reloader=False,
            debug=True  # Enable debug mode for better error reporting
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
        logger.info("Initializing MongoDB...")
        if not init_mongodb():
            raise Exception("Failed to initialize MongoDB")
        
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