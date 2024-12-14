# wsgi.py
from server import create_app
from waitress import serve
from api import setup_bot
import os
from dotenv import load_dotenv

app = create_app()

if __name__ == "__main__":

    host = 'localhost'  # Changed from 0.0.0.0 to localhost
    port = 3306
    
    serve(app, host=host, port=port, threads=6)
    
    load_dotenv()
    
    setup_bot()