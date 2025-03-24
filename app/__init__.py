from flask import Flask
from app.config.settings import Config
import os
import sys

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
        
        # Verify critical paths exist
        if not os.path.exists(app.template_folder):
            raise RuntimeError(f"Template folder not found: {app.template_folder}")
        if not os.path.exists(app.static_folder):
            raise RuntimeError(f"Static folder not found: {app.static_folder}")
            
        return app
    except Exception as e:
        print(f"Error creating app: {str(e)}", file=sys.stderr)
        raise
