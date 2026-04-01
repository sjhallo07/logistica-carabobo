import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
dsn = os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit('DATABASE_URL not set in .env')

SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'sql', 'create_match_documents.sql')

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                cur.execute(f.read())
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            raise RuntimeError(f"Error executing SQL from '{sql_file_path}': {e}") from e
