import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Add this for debugging
if not app:
    raise RuntimeError("Failed to create Flask application") 