from datetime import datetime, timedelta
from db.database import db
from pymongo import DESCENDING

class PastebinModel:
    def __init__(self):
        # Access the collection directly through the database instance
        self.collection = db.client['telegram_bot']['pastebin_entries']
        # Create indexes
        self.collection.create_index([('user_id', DESCENDING)])
        self.collection.create_index([('created_at', DESCENDING)])
        self.collection.create_index('username')  # Add index for username

    def create_entry(self, user_id, content, title=None, username=None):
        """Create a new pastebin entry"""
        entry = {
            'user_id': user_id,
            'username': username or "Unknown",  # Store username
            'content': content,
            'title': title or f'Decrypted_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'created_at': datetime.utcnow(),
            'url': None
        }
        result = self.collection.insert_one(entry)
        return result.inserted_id
    
    def update_paste_url(self, entry_id, url):
        """Update the entry with the Pastebin URL"""
        self.collection.update_one(
            {'_id': entry_id},
            {'$set': {'url': url, 'updated_at': datetime.utcnow()}}
        )
    
    def get_user_pastes(self, user_id, limit=10):
        """Get user's latest pastes"""
        return list(self.collection.find(
            {'user_id': user_id},
            {'_id': 0, 'content': 0}  # Exclude content for efficiency
        ).sort('created_at', DESCENDING).limit(limit))
    
    def get_paste_by_username(self, username, limit=10):
        """Get pastes by username"""
        return list(self.collection.find(
            {'username': username},
            {'_id': 0, 'content': 0}
        ).sort('created_at', DESCENDING).limit(limit))
    
    def get_paste(self, entry_id):
        """Get a specific paste"""
        return self.collection.find_one({'_id': entry_id})
    
    def delete_old_pastes(self, days=30):
        """Delete pastes older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        self.collection.delete_many({'created_at': {'$lt': cutoff_date}})

# Initialize the model
pastebin_db = PastebinModel()