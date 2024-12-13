from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from threading import Thread
from api import setup_bot
from db.database import db
from dotenv import load_dotenv
import os
import sys
import logging
from datetime import datetime
import json
from routes.admin import init_admin_routes
from routes.api import register_api_routes

# Configure logger at module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    CORS(app)
    
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'js'), exist_ok=True)

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        response = send_from_directory(app.static_folder, filename)
        response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.route('/')
    def home():
        try:
            users = list(db.users.users.find({}, {'_id': 0}))
            transactions = list(db.transactions.transactions.find(
                {}, {'_id': 0}
            ).sort('created_at', -1).limit(100))
            return render_template('index.html', users=users, transactions=transactions)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return render_template('error.html', error="Unable to load dashboard"), 500

    @app.route('/health')
    def health():
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

    init_admin_routes(app)
    register_api_routes(app)
    
    return app

def main():
    try:
        load_dotenv()
        
        if not os.getenv('MONGO_URI'):
            raise ValueError("MONGO_URI environment variable is not set")

        db.client.admin.command('ping')
        logger.info("🚀 MongoDB connection successful")
        logger.info("🚀 Starting server...")

        app = create_app()
        
        # Start Flask in a separate thread
        flask_thread = Thread(target=lambda: app.run(
            host='0.0.0.0',
            port=3306,
            use_reloader=False,
            debug=False
        ))
        flask_thread.daemon = True
        flask_thread.start()

        # Run the bot in the main thread
        setup_bot()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()