import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load .env from project root
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL not set in environment. Please configure .env or environment variables.')

# Simple helper to get a connection
def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Example usage: fetch version
if __name__ == '__main__':
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT version();')
            print(cur.fetchone())
    finally:
        conn.close()
