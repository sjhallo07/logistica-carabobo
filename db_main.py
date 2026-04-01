import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment (.env)")

def main():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute('SELECT version();')
        print('Connected to:', cur.fetchone())
        cur.close()
        conn.close()
    except Exception as e:
        print('Error connecting to database:', e)

if __name__ == '__main__':
    main()
