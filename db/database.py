import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'botuser'),
            password=os.getenv('DB_PASSWORD', 'your_password'),
            database=os.getenv('DB_NAME', 'telegram_bot'),
            port=int(os.getenv('DB_PORT', '3306')),
            ssl_mode = os.getenv('DB_SSL_MODE', None)  # Optional: for SSL connection
        )
        
        # Disable safe updates when connection is established
        cursor = connection.cursor()
        cursor.execute("SET SQL_SAFE_UPDATES = 0")
        cursor.close()
        
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

def initialize_database():
    connection = get_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    coins INT DEFAULT 0,
                    last_daily DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    amount INT,
                    type VARCHAR(50),
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            connection.commit()
            print("Database initialized successfully")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            connection.close()