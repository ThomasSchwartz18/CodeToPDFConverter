import os
import tempfile

# Use the system’s temporary directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".mp4", ".mp3"}
TEXT_EXTENSIONS = {".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json", ".md", ".php", ".sql"}

# Ensure the directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database configuration
DATABASE_CONFIG = {
    'dbname': 'code_to_pdf',  # Your database name
    'user': 'postgres',       # Your PostgreSQL username
    'password': 'PostgreMoose58',  # Your PostgreSQL password
    'host': 'localhost',      # Your PostgreSQL host
    'port': 5432              # Your PostgreSQL port
}