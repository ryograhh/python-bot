# services/bot_manager.py
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
import telegram
import logging
import asyncio
from threading import Thread, Lock
from pathlib import Path
import importlib
import sys

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.bots = {}
        self.bot_threads = {}
        self.commands = {}
        self.lock = Lock()
        
    def load_commands(self):
        """Load commands from commands directory"""
        commands = {}
        try:
            # Add commands directory to Python path
            commands_path = str(Path('commands').absolute())
            if commands_path not in sys.path:
                sys.path.append(commands_path)
                
            command_files = list(Path('commands').glob('*.py'))
            logger.info(f"Found command files: {[f.stem for f in command_files]}")
            
            for file in command_files:
                if file.stem != '__init__':
                    command_name = file.stem
                    try:
                        # Force reload the module
                        if command_name in sys.modules:
                            del sys.modules[command_name]
                        module = importlib.import_module(command_name)
                        if hasattr(module, 'handle'):
                            commands[command_name] = module.handle
                            logger.info(f"Successfully loaded command: {command_name}")
                    except Exception as e:
                        logger.error(f"Error loading command {command_name}: {e}")
        except Exception as e:
            logger.error(f"Error loading commands directory: {e}")
            
        self.commands = commands
        return commands

    def start_bot(self, bot_id: str, token: str, message_handler=None):
        """Start a new bot instance"""
        try:
            with self.lock:
                if bot_id in self.bots:
                    logger.warning(f"Bot {bot_id} is already running")
                    return True

                # Create event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Verify token
                if not loop.run_until_complete(self.verify_token(token)):
                    logger.error(f"Invalid token for bot {bot_id}")
                    loop.close()
                    return False

                # Load commands
                self.load_commands()

                # Create application instance
                application = ApplicationBuilder().token(token).build()
                
                # Add command handlers
                for cmd_name, cmd_handler in self.commands.items():
                    application.add_handler(CommandHandler(cmd_name, cmd_handler))
                    logger.info(f"Added command handler for: {cmd_name}")

                # Add message handler for text commands
                application.add_handler(MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    self.handle_text_command
                ))
                
                # Store bot instance
                self.bots[bot_id] = {
                    'app': application,
                    'token': token,
                    'loop': loop,
                    'thread': None
                }
                
                # Start bot in a new thread
                thread = Thread(target=self._run_bot, args=(bot_id,))
                thread.daemon = True
                thread.start()
                
                # Store thread reference
                self.bots[bot_id]['thread'] = thread
                self.bot_threads[bot_id] = thread
                
                logger.info(f"Bot {bot_id} started successfully with {len(self.commands)} commands")
                return True
            
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {str(e)}")
            with self.lock:
                if bot_id in self.bots:
                    del self.bots[bot_id]
                if bot_id in self.bot_threads:
                    del self.bot_threads[bot_id]
            return False

    async def handle_text_command(self, update, context):
        """Handle text messages as potential commands"""
        try:
            if not update.message or not update.message.text:
                return

            text = update.message.text.lower().strip()
            first_word = text.split()[0]

            if first_word in self.commands:
                logger.info(f"Executing text command: {first_word}")
                await self.commands[first_word](update, context)
                
        except Exception as e:
            logger.error(f"Error handling text command: {e}")

    async def verify_token(self, token):
        """Verify if the token is valid"""
        try:
            bot = telegram.Bot(token)
            bot_info = await bot.get_me()
            logger.info(f"Verified bot: {bot_info.first_name} (@{bot_info.username})")
            return True
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False

    def _run_bot(self, bot_id):
        """Run the bot application"""
        try:
            if bot_id not in self.bots:
                return
                
            bot_data = self.bots[bot_id]
            loop = bot_data['loop']
            app = bot_data['app']
            
            asyncio.set_event_loop(loop)
            
            # Initialize and start the application
            loop.run_until_complete(app.initialize())
            loop.run_until_complete(app.start())
            logger.info(f"Bot {bot_id} is now polling for updates")
            
            # Start polling with specific parameters
            loop.run_until_complete(app.updater.start_polling(
                allowed_updates=['message'],
                drop_pending_updates=True
            ))
            loop.run_forever()
            
        except Exception as e:
            logger.error(f"Bot runtime error for {bot_id}: {str(e)}")
        finally:
            self._cleanup_bot(bot_id)

    def _cleanup_bot(self, bot_id):
        """Clean up bot resources"""
        try:
            with self.lock:
                if bot_id in self.bots:
                    bot_data = self.bots[bot_id]
                    
                    # Get references before deletion
                    loop = bot_data['loop']
                    app = bot_data['app']
                    
                    # Stop polling first
                    if hasattr(app, 'updater') and app.updater.running:
                        if not loop.is_closed():
                            loop.run_until_complete(app.updater.stop())
                    
                    # Then stop the application
                    if not loop.is_closed():
                        loop.run_until_complete(app.stop())
                        loop.stop()
                        loop.close()
                    
                    # Clean up references
                    del self.bots[bot_id]
                    
                if bot_id in self.bot_threads:
                    del self.bot_threads[bot_id]
                    
        except Exception as e:
            logger.error(f"Error during cleanup for bot {bot_id}: {e}")

    def stop_bot(self, bot_id: str):
        """Stop a running bot instance"""
        try:
            with self.lock:
                if bot_id in self.bots:
                    bot_data = self.bots[bot_id]
                    loop = bot_data['loop']
                    app = bot_data['app']
                    
                    # First stop the updater
                    if hasattr(app, 'updater') and app.updater.running:
                        loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(app.updater.stop())
                        )
                    
                    # Then stop the application
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(app.stop())
                    )
                    
                    # Wait for thread to finish
                    thread = bot_data['thread']
                    if thread and thread.is_alive():
                        thread.join(timeout=5)
                    
                    # Clean up
                    self._cleanup_bot(bot_id)
                    logger.info(f"Bot {bot_id} stopped successfully")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to stop bot {bot_id}: {str(e)}")
            return False
    
    def get_active_bots(self):
        """Get list of active bot IDs"""
        return list(self.bots.keys())
    
    def is_bot_running(self, bot_id: str):
        """Check if a bot is running"""
        with self.lock:
            return (bot_id in self.bots and 
                   bot_id in self.bot_threads and 
                   self.bot_threads[bot_id].is_alive())

# Global bot manager instance
bot_manager = BotManager()