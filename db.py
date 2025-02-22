import psycopg2
from dotenv import load_dotenv
import os


load_dotenv()  # Load environment variables from .env file

DATABASE_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    """Connect to the PostgreSQL database."""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    return conn

def create_user(username, password):
    """Insert a new user into the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password))
        conn.commit()
    except psycopg2.IntegrityError:
        return False  # Username already exists
    finally:
        cur.close()
        conn.close()
    return True

def get_user_by_username(username):
    """Retrieve a user by their username."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user