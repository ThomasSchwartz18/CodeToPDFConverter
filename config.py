import os

UPLOAD_DIR = "/mnt/data/uploads"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"}
TEXT_EXTENSIONS = {".py", ".txt", ".html", ".js", ".css", ".java", ".cpp", ".c", ".json", ".md"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
