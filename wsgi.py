# wsgi.py
from server import create_app
from waitress import serve
from api import setup_bot
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Create the Flask app
app = create_app()

# Setup the bot before starting the server
setup_bot()

if __name__ == "__main__":
    host = '0.0.0.0'
    port = 3306
    
    # Start the server (this should be last as it's blocking)
    serve(app, host=host, port=port, threads=6)