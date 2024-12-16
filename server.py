# server.py
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_cors import CORS
from services.bot_manager import bot_manager
from db.database import db
import logging
from bson import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def create_app():
    app = Flask(__name__)
    app.secret_key = 'Jubiar'  # Change this in production
    CORS(app)

    @app.route('/')
    @login_required
    def home():
        try:
            user_bots = db.bot_tokens.get_user_bots(
                session['username'],
                db.users_auth.get_encryption_key(session['username'])
            )
            # Update bot status from bot manager
            for bot in user_bots:
                bot['is_active'] = bot_manager.is_bot_running(str(bot['_id']))
            
            return render_template('dashboard.html', bots=user_bots)
        except Exception as e:
            logger.error(f"Error in home route: {str(e)}")
            return render_template('error.html', error=str(e))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                return render_template('login.html', error="Username and password are required")
            
            try:
                user = db.users_auth.verify_user(username, password)
                if user:
                    session['username'] = username
                    return redirect(url_for('home'))
                return render_template('login.html', error="Invalid credentials")
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                return render_template('login.html', error="Login failed")
        
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                return render_template('register.html', error="Username and password are required")
                
            try:
                db.users_auth.create_user(username, password)
                session['username'] = username
                return redirect(url_for('home'))
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return render_template('register.html', error=str(e))
        
        return render_template('register.html')

    @app.route('/api/bots', methods=['POST'])
    @login_required
    def add_bot():
        try:
            data = request.get_json()
            token = data.get('token')
            bot_name = data.get('bot_name')
            
            if not token or not bot_name:
                return jsonify({'error': 'Missing required fields'}), 400
                
            encryption_key = db.users_auth.get_encryption_key(session['username'])
            bot_id = db.bot_tokens.create_bot(
                session['username'],
                token,
                bot_name,
                encryption_key
            )
            
            success = bot_manager.start_bot(str(bot_id.inserted_id), token)
            
            if success:
                return jsonify({'message': 'Bot added successfully'}), 200
            return jsonify({'error': 'Failed to start bot'}), 500
            
        except Exception as e:
            logger.error(f"Error adding bot: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bots/<bot_id>', methods=['DELETE'])
    @login_required
    def remove_bot(bot_id):
        try:
            # Stop the bot first
            bot_manager.stop_bot(bot_id)
            
            # Then delete from database
            result = db.bot_tokens.delete_bot(ObjectId(bot_id), session['username'])
            
            if result and result.deleted_count > 0:
                return jsonify({'message': 'Bot removed successfully'}), 200
            return jsonify({'error': 'Bot not found or unauthorized'}), 404
        except Exception as e:
            logger.error(f"Error removing bot: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bots/<bot_id>/start', methods=['POST'])
    @login_required
    def start_bot(bot_id):
        try:
            bot = db.bot_tokens.get_bot(ObjectId(bot_id), session['username'])
            if bot:
                success = bot_manager.start_bot(bot_id, bot['token'])
                if success:
                    db.bot_tokens.update_bot_status(ObjectId(bot_id), True)
                    return jsonify({'message': 'Bot started successfully'}), 200
            return jsonify({'error': 'Failed to start bot'}), 500
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bots/<bot_id>/stop', methods=['POST'])
    @login_required
    def stop_bot(bot_id):
        try:
            success = bot_manager.stop_bot(bot_id)
            if success:
                db.bot_tokens.update_bot_status(ObjectId(bot_id), False)
                return jsonify({'message': 'Bot stopped successfully'}), 200
            return jsonify({'error': 'Failed to stop bot'}), 500
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    return app

def main():
    try:
        app = create_app()
        app.run(host='0.0.0.0', port=3306, debug=True)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

if __name__ == "__main__":
    main()