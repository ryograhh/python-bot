# db/database.py
import logging
from .config import get_mongo_client, DB_NAME
from .models import UserModel, TransactionModel, AdminCodeModel

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = get_mongo_client()
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            db = self.client[DB_NAME]
            self._create_indexes(db)
            
            # Initialize models
            self.users = UserModel(db)
            self.transactions = TransactionModel(db)
            self.admin_codes = AdminCodeModel(db)
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            raise

    def _create_indexes(self, db):
        """Create necessary indexes"""
        try:
            db.users.create_index('user_id', unique=True)
            db.users.create_index('username')
            db.transactions.create_index([('user_id', 1), ('created_at', -1)])
            db.admin_codes.create_index('code', unique=True)
            db.admin_codes.create_index('created_at')
            db.admin_codes.create_index('used_by')
            logger.info("✅ MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {str(e)}")
            raise

    def __del__(self):
        """Cleanup method to close MongoDB connection"""
        try:
            self.client.close()
        except:
            pass

# Create global database instance
try:
    db = Database()
except Exception as e:
    logger.critical(f"❌ Failed to initialize MongoDB: {str(e)}")
    raise