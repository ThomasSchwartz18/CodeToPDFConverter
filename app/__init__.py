from flask import Flask, current_app
from app.config.settings import Config
import os
import sys
import threading
import time
from app.utils.logger import setup_logger
from app.services.file_processor import FileProcessor

logger = setup_logger(__name__)

def start_cleanup_thread():
    """Start a background thread for automatic cleanup of stale uploads."""
    def run_cleanup():
        while True:
            try:
                time.sleep(1800)  # Cleanup every 30 minutes
                FileProcessor.cleanup_stale_uploads(age_limit_seconds=3600)
                logger.info("Automatic cleanup executed successfully")
            except Exception as e:
                logger.error(f"Error in automatic cleanup: {str(e)}")

    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("Automatic cleanup thread started")

def create_app(config_class=Config):
    try:
        # Get the absolute path to the root directory
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        app = Flask(__name__, 
                    template_folder=os.path.join(root_dir, 'templates'),
                    static_folder=os.path.join(root_dir, 'static'))
        
        app.config.from_object(config_class)
        
        # Register blueprints
        from app.routes.main import main_bp
        from app.routes.api import api_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # Register CLI commands
        from app.cli import cleanup_uploads
        app.cli.add_command(cleanup_uploads)
        
        # Verify critical paths exist
        if not os.path.exists(app.template_folder):
            raise RuntimeError(f"Template folder not found: {app.template_folder}")
        if not os.path.exists(app.static_folder):
            raise RuntimeError(f"Static folder not found: {app.static_folder}")
            
        # Ensure critical directories exist
        config_class.ensure_directories()
        
        # Start automatic cleanup thread
        with app.app_context():
            start_cleanup_thread()
        
        logger.info("Application initialized successfully")
        return app
    except Exception as e:
        logger.error(f"Error creating app: {str(e)}")
        raise
