# wsgi.py
from server import create_app
from waitress import serve
from api import setup_bot
import os
from dotenv import load_dotenv
import threading
import asyncio

async def run_bot_async():
    """Run the Telegram bot asynchronously"""
    try:
        await setup_bot()
    except Exception as e:
        print(f"Error in bot thread: {e}")

def run_bot():
    """Run the bot in a separate thread with proper async handling"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot_async())
        loop.run_forever()
    except Exception as e:
        print(f"Error in bot thread: {e}")
    finally:
        loop.close()

def run_server(app, host, port):
    """Run the Flask server"""
    print(f"Starting server on {host}:{port}")
    serve(app, host=host, port=port, threads=6)

def main():
    # Load environment variables first
    load_dotenv()
    
    # Create Flask app
    app = create_app()
    
    # Server configuration
    host = '0.0.0.0'
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 3306))
    
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the server in the main thread
    run_server(app, host, port)

# This ensures the app can be imported by WSGI servers
app = create_app()

if __name__ == "__main__":
    main()