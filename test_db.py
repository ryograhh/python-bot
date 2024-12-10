from db.database import get_database_connection

def test_connection():
    connection = get_database_connection()
    if connection:
        print("Successfully connected to MySQL database!")
        cursor = connection.cursor()
        
        # Test query
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("Available tables:", tables)
        
        cursor.close()
        connection.close()
    else:
        print("Failed to connect to database!")

if __name__ == "__main__":
    test_connection()