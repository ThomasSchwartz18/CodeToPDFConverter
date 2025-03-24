from flask import Flask
from app.config.settings import Config
import os
import logging
from logging.handlers import RotatingFileHandler

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.config.from_object(config_class)
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/unifydoc.log',
                                         maxBytes=10240,
                                         backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('UnifyDoc startup')
    
    # Ensure upload directory exists with proper permissions
    try:
        os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)
        # Ensure directory has proper permissions
        os.chmod(app.config['UPLOAD_DIR'], 0o755)
        app.logger.info(f"Upload directory created at {app.config['UPLOAD_DIR']}")
    except Exception as e:
        app.logger.error(f"Error creating upload directory: {str(e)}")
        # Try alternative location if on Heroku
        if 'DYNO' in os.environ:
            try:
                app.config['UPLOAD_DIR'] = '/tmp'
                app.logger.info("Using /tmp as upload directory on Heroku")
            except Exception as e:
                app.logger.error(f"Error using alternative upload directory: {str(e)}")
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
