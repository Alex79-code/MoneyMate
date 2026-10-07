
from db import get_db_connection

try:
    connection = get_db_connection()

    if connection.is_connected():
        print("MoneyMate connected to MySQL successfully!")

    connection.close()

except Exception as error:
    print("Database connection failed:", error)