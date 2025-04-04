import os
import tempfile
import secrets

class Config:
    # File upload settings
    UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max file size
    
    # File extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    TEXT_EXTENSIONS = {
        ".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json",
        ".md", ".php", ".sql", ".doc", ".docx", ".pdf"
    }
    
    # Security
    SECRET_KEY = secrets.token_hex(16)
    
    # PDF Settings
    DEFAULT_FONT_SIZE = 10
    DEFAULT_LINE_HEIGHT = 12
    DEFAULT_MARGIN = 10
    MAX_CHARS_PER_LINE = 90
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True) 