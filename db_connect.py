import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env
load_dotenv()

# Fetch the DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment (.env). Set it before running this script.")

def test_connection():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT version();')
        ver = cur.fetchone()
        print('Connected to:', ver)
        cur.close()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    test_connection()
