import os
import tempfile
# Use the system's temporary directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
TEXT_EXTENSIONS = {".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json",
                   ".md", ".php", ".sql", ".doc", ".docx", ".pdf"}
# Ensure the directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)
