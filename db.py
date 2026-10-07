import os
import mysql.connector


def get_db_connection():
    mysql_password = os.getenv("MONEYMATE_DB_PASSWORD")

    if not mysql_password:
        raise Exception(
            "MONEYMATE_DB_PASSWORD environment variable is not set."
        )

    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=mysql_password,
        database="moneymate",
        port=3306
    )

    return connection