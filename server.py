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

# Set up logging with more verbose output
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Flask with template folder
app = Flask(__name__, template_folder='templates')

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

def parse_json(data):
    """Custom JSON parser for MongoDB data"""
    return json.loads(json_util.dumps(data))

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
        return client, db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

@app.route('/')
def home():
    """Render the dashboard template"""
    try:
        client, db = get_db()
        
        # Get all users and transactions with basic fields
        users = list(db.users.find({}, {'_id': 0}))
        transactions = list(db.transactions.find({}, {'_id': 0}).limit(100))  # Limit to last 100 transactions
        
        # Convert MongoDB data to JSON-serializable format
        users_json = parse_json(users)
        transactions_json = parse_json(transactions)
        
        client.close()
        
        return render_template(
            'index.html',
            users=users_json,
            transactions=transactions_json
        )
        
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        # Return a user-friendly error page
        return render_template(
            'error.html',
            error="Unable to load dashboard. Please try again later."
        ), 500

@app.route('/api/users')
def get_users():
    """API endpoint to get all users"""
    try:
        client, db = get_db()
        users = list(db.users.find({}, {'_id': 0}))
        client.close()
        return jsonify(parse_json(users))
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/transactions')
def get_transactions():
    """API endpoint to get transactions"""
    try:
        client, db = get_db()
        transactions = list(db.transactions.find({}, {'_id': 0}).limit(100))
        client.close()
        return jsonify(parse_json(transactions))
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
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500

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
        
        # Verify database connection
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