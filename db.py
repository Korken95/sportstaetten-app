# db.py

import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Techlabs#2025",
        database="techlabs_projekt"
    )
