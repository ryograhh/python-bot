from flask import Flask, render_template
from threading import Thread
from api import setup_bot
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')
MONGO_TIMEOUT = int(os.getenv('MONGO_CONNECTION_TIMEOUT', '30000'))

def get_db():
    """Get MongoDB client and database"""
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        retryWrites=True,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    return client, client[DB_NAME]

def init_mongodb():
    """Initialize MongoDB connection and create indexes"""
    try:
        client, db = get_db()
        
        # Test connection
        client.admin.command('ping')
        
        # Create collections if they don't exist
        existing_collections = db.list_collection_names()
        if 'users' not in existing_collections:
            logger.info("Creating users collection...")
            db.create_collection('users')
        if 'transactions' not in existing_collections:
            logger.info("Creating transactions collection...")
            db.create_collection('transactions')
            
        # Create indexes with background=True
        logger.info("Creating indexes...")
        db.users.create_index('user_id', unique=True, background=True)
        db.users.create_index('username', background=True)
        db.transactions.create_index([('user_id', 1), ('created_at', -1)], background=True)
        
        logger.info("✅ MongoDB connection and setup successful")
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during MongoDB initialization: {str(e)}")
        return False

@app.route('/')
def home():
    try:
        client, db = get_db()
        
        # Get all users and transactions
        users = list(db.users.find({}, {'_id': 0}))
        transactions = list(db.transactions.find({}, {'_id': 0}))
        
        # Convert datetime objects to strings for JSON serialization
        for transaction in transactions:
            if 'created_at' in transaction:
                transaction['created_at'] = transaction['created_at'].isoformat()
        
        for user in users:
            if 'last_daily' in user and user['last_daily']:
                user['last_daily'] = user['last_daily'].isoformat()
            if 'created_at' in user and user['created_at']:
                user['created_at'] = user['created_at'].isoformat()
        
        client.close()
        
        return render_template('index.html', users=users, transactions=transactions)
        
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return "Error loading dashboard", 500

@app.route('/health')
def health():
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,  # Short timeout for health check
            connectTimeoutMS=5000
        )
        # Test connection
        client.admin.command('ping')
        client.close()
        return {
            "status": "healthy",
            "database": "connected"
        }, 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }, 500

def run_flask():
    """Run Flask server with error handling"""
    try:
        app.run(
            host='0.0.0.0',
            port=3306,
            use_reloader=False  # Disable reloader when running in thread
        )
    except Exception as e:
        logger.error(f"❌ Flask server error: {str(e)}")
        sys.exit(1)

def run_bot():
    """Run Telegram bot with error handling"""
    try:
        setup_bot()
    except Exception as e:
        logger.error(f"❌ Telegram bot error: {str(e)}")
        sys.exit(1)

def main():
    try:
        # Check if required environment variables are set
        if not MONGO_URI:
            logger.error("❌ MONGO_URI environment variable is not set")
            sys.exit(1)
        
        # Initialize MongoDB
        logger.info("Initializing MongoDB...")
        if not init_mongodb():
            logger.error("❌ Failed to initialize MongoDB")
            sys.exit(1)
        
        logger.info("🚀 Starting server...")
        
        # Start Flask in a separate thread
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        flask_thread.start()
        
        # Run the bot in the main thread
        run_bot()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()