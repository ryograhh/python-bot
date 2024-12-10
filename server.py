from flask import Flask
from threading import Thread
from api import setup_bot
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://biaronab:Yg1cxmqdHZgkjywD@cluster0.vm9kj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DB_NAME = os.getenv('DB_NAME', 'telegram_bot')

def init_mongodb():
    """Initialize MongoDB connection and create indexes"""
    try:
        # Create MongoDB client
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Get database
        db = client[DB_NAME]
        
        # Create collections if they don't exist
        if 'users' not in db.list_collection_names():
            db.create_collection('users')
        if 'transactions' not in db.list_collection_names():
            db.create_collection('transactions')
            
        # Create indexes
        db.users.create_index('user_id', unique=True)
        db.users.create_index('username')
        db.transactions.create_index('user_id')
        db.transactions.create_index('created_at')
        
        print("✅ MongoDB connection successful")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        return False

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    try:
        # Check MongoDB connection
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        return "OK", 200
    except:
        return "Database Error", 500

def run_flask():
    app.run(host='0.0.0.0', port=3306)

def run_bot():
    setup_bot()

def main():
    # Initialize MongoDB
    if not init_mongodb():
        print("❌ Failed to initialize MongoDB. Exiting...")
        sys.exit(1)
    
    print("🚀 Starting server...")
    
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Run the bot in the main thread
    run_bot()

if __name__ == "__main__":
    main()