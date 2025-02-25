import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

connection_string = os.getenv('DATABASE_URL')
print("Connection string:", connection_string)  # Debug print

def get_db_connection():
    """Connect to the PostgreSQL database using a full connection string."""
    connection_string = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(connection_string, sslmode='require')
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

def get_user_by_id(user_id):
    """Retrieve a user by their id."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user