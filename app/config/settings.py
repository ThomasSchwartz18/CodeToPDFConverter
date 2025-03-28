import os
import tempfile
import secrets
from datetime import timedelta

class Config:
    # File upload settings
    # Use a directory relative to the app root for better reliability
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max file size
    
    # File extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    TEXT_EXTENSIONS = {
        ".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json",
        ".md", ".php", ".sql", ".doc", ".docx", ".pdf"
    }
    
    # Security
    # Use environment variable for SECRET_KEY, fallback to a secure random key
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # PDF Settings
    DEFAULT_FONT_SIZE = 10
    DEFAULT_LINE_HEIGHT = 12
    DEFAULT_MARGIN = 10
    MAX_CHARS_PER_LINE = 90
    
    # Ensure critical directories exist
    @classmethod
    def init_app(cls, app):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True) 

    @staticmethod
    def ensure_directories():
        """Ensure all required directories exist."""
        os.makedirs(Config.UPLOAD_DIR, exist_ok=True) 