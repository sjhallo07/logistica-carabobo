import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
dsn = os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit('DATABASE_URL not set in .env')

SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'sql', 'create_match_documents.sql')

sql_file_path = os.path.abspath(SQL_FILE)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            cur.execute(sql)
            conn.commit()
            print(f"Executed SQL file: {sql_file_path}")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error executing SQL from '{sql_file_path}': {e}")
            raise
