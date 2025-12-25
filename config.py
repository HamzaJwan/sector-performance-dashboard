import os
import time
import mysql.connector
from contextlib import contextmanager

DB_CONFIG = {
    "host": os.getenv("SECT_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("SECT_DB_PORT", "3307")),
    "user": os.getenv("SECT_DB_USER", "root"),
    "password": os.getenv("SECT_DB_PASS", "strongpass123"),
    "database": os.getenv("SECT_DB_NAME", "Sectors"),
    "connection_timeout": 5,
    "autocommit": True,
}

@contextmanager
def db_connection(retries=5, sleep_s=1.0):
    last = None
    for _ in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            try:
                yield conn
            finally:
                try: conn.close()
                except: pass
            return
        except Exception as e:
            last = e
            time.sleep(sleep_s)
    raise last
