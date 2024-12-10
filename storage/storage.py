from datetime import datetime, timedelta
import json
import os

class Storage:
    def __init__(self):
        self.users = {}
        self.transactions = {}
        self.load_data()

    def load_data(self):
        """Load data from JSON files if they exist"""
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                self.users = json.load(f)
                # Convert string dates back to datetime objects
                for user_data in self.users.values():
                    if user_data.get('last_daily'):
                        user_data['last_daily'] = datetime.fromisoformat(user_data['last_daily'])

        if os.path.exists('transactions.json'):
            with open('transactions.json', 'r') as f:
                self.transactions = json.load(f)
                # Convert string dates back to datetime objects
                for user_id in self.transactions:
                    for tx in self.transactions[user_id]:
                        tx['created_at'] = datetime.fromisoformat(tx['created_at'])

    def save_data(self):
        """Save data to JSON files"""
        # Convert datetime objects to strings for JSON serialization
        users_to_save = {}
        for user_id, user_data in self.users.items():
            users_to_save[user_id] = user_data.copy()
            if users_to_save[user_id].get('last_daily'):
                users_to_save[user_id]['last_daily'] = user_data['last_daily'].isoformat()

        transactions_to_save = {}
        for user_id, txs in self.transactions.items():
            transactions_to_save[user_id] = []
            for tx in txs:
                tx_copy = tx.copy()
                tx_copy['created_at'] = tx['created_at'].isoformat()
                transactions_to_save[user_id].append(tx_copy)

        with open('users.json', 'w') as f:
            json.dump(users_to_save, f, indent=2)

        with open('transactions.json', 'w') as f:
            json.dump(transactions_to_save, f, indent=2)

    def get_user(self, user_id, username=None):
        """Get or create user"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'username': username or 'Unknown',
                'coins': 0,
                'last_daily': None
            }
            self.save_data()
        return self.users[user_id]

    def update_user_coins(self, user_id, amount):
        """Update user's coin balance"""
        user_id = str(user_id)
        user = self.get_user(user_id)
        user['coins'] += amount
        self.save_data()
        return user['coins']

    def add_transaction(self, user_id, amount, type_, description):
        """Add a transaction record"""
        user_id = str(user_id)
        if user_id not in self.transactions:
            self.transactions[user_id] = []
        
        self.transactions[user_id].append({
            'amount': amount,
            'type': type_,
            'description': description,
            'created_at': datetime.now()
        })
        self.save_data()

    def get_transactions(self, user_id, limit=5):
        """Get user's transaction history"""
        user_id = str(user_id)
        if user_id not in self.transactions:
            return []
        return sorted(self.transactions[user_id], 
                     key=lambda x: x['created_at'], 
                     reverse=True)[:limit]

    def update_last_daily(self, user_id):
        """Update user's last daily claim time"""
        user_id = str(user_id)
        user = self.get_user(user_id)
        user['last_daily'] = datetime.now()
        self.save_data()

# Create global storage instance
storage = Storage()