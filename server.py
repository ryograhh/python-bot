from flask import Flask
from threading import Thread
from api import setup_bot
from db.database import initialize_database

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=3306)

def run_bot():
    initialize_database()
    setup_bot()

def main():
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Run the bot in the main thread
    run_bot()

if __name__ == "__main__":
    main()