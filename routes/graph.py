from flask import render_template, jsonify, current_app
from datetime import datetime, timedelta
from db.database import db

def init_graph_routes(app):
    @app.route('/graph')
    def graph_page():
        """Render the graph analytics page"""
        return render_template('graph.html')

    @app.route('/api/graph/transactions')
    def graph_transactions():
        """Get all transactions for the graph visualization"""
        try:
            # Get transactions from the last year
            one_year_ago = datetime.now() - timedelta(days=365)
            transactions = list(db.transactions.transactions.find(
                {"created_at": {"$gte": one_year_ago}},
                {'_id': 0}
            ).sort('created_at', 1))
            
            # Convert datetime objects to ISO format
            for transaction in transactions:
                if isinstance(transaction.get('created_at'), datetime):
                    transaction['created_at'] = transaction['created_at'].isoformat()
            
            return jsonify(transactions)
        except Exception as e:
            current_app.logger.error(f"Error fetching graph transactions: {str(e)}")
            return jsonify({"error": "Failed to fetch transactions"}), 500

    @app.route('/api/graph/users')
    def graph_users():
        """Get all users for the graph visualization"""
        try:
            users = list(db.users.users.find({}, {'_id': 0}))
            return jsonify(users)
        except Exception as e:
            current_app.logger.error(f"Error fetching graph users: {str(e)}")
            return jsonify({"error": "Failed to fetch users"}), 500