# db/models/transaction.py
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TransactionModel:
    def __init__(self, db):
        self.transactions = db.transactions

    def add_transaction(self, user_id: str, amount: int, type_: str, description: str):
        """Add a transaction record"""
        try:
            transaction = {
                'user_id': user_id,
                'amount': amount,
                'type': type_,
                'description': description,
                'created_at': datetime.now()
            }
            self.transactions.insert_one(transaction)
        except Exception as e:
            logger.error(f"Error adding transaction: {str(e)}")
            raise

    def get_transactions(self, user_id: str, limit: int = 5) -> list:
        """Get user's transaction history"""
        try:
            return list(self.transactions.find(
                {'user_id': user_id},
                {'_id': 0}
            ).sort('created_at', -1).limit(limit))
        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            raise