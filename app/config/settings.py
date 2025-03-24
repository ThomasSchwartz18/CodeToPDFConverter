import os
import secrets

class Config:
    # Environment
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'
    
    # File upload settings
    UPLOAD_DIR = '/tmp'  # Use /tmp directory on Heroku and locally for simplicity
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max file size
    
    # File extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    TEXT_EXTENSIONS = {
        ".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json",
        ".md", ".php", ".sql", ".doc", ".docx", ".pdf"
    }
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    
    # PDF Settings
    DEFAULT_FONT_SIZE = 10
    DEFAULT_LINE_HEIGHT = 12
    DEFAULT_MARGIN = 10
    MAX_CHARS_PER_LINE = 90
    
    # Ensure critical directories exist
    @classmethod
    def init_app(cls, app):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True) 