import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER") 
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
SQL_FILE_PATH = Path(__file__).parent / "init_db_schema.sql"


# --- Execution ---
def execute_sql_file():
    try:
        with psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        ) as conn:
            with conn.cursor() as cur:
                sql = Path(SQL_FILE_PATH).read_text()
                print(sql)
                cur.execute(sql)
                conn.commit()
                print("✅ Database schema created successfully.")

    except Exception as e:
        print("❌ Failed to create database schema:")
        print(e)

if __name__ == "__main__":
    execute_sql_file()
