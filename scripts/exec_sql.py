import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'sql', 'create_match_documents.sql')

if not DATABASE_URL:
    raise SystemExit('DATABASE_URL not set in .env')

with open(SQL_FILE, 'r', encoding='utf-8') as f:
    sql = f.read()

print('Connecting to database...')
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()
try:
    print('Executing SQL...')
    cur.execute(sql)
    print('SQL executed successfully')
except Exception as e:
    print('Error executing SQL:', e)
    raise
finally:
    cur.close()
    conn.close()
