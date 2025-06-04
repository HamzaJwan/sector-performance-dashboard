import mysql.connector
from contextlib import contextmanager

DB_CONFIG = {
    'host': '172.31.1.70',
    'user': 'root',
    'password': 'strongpass123',
    'database': 'Sectors',
    'port': 3307
}

@contextmanager
def db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
