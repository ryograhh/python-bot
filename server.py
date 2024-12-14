from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from db.database import db
from dotenv import load_dotenv
import os
import sys
import logging
from datetime import datetime
import json
from routes.admin import init_admin_routes
from routes.api import register_api_routes
from routes.graph import init_graph_routes

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
    init_graph_routes(app)
    
    return app