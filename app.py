import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask, render_template
from config import Config
from routes.auth import auth_bp
from routes.documents import documents_bp
from routes.folders import folders_bp
from routes.sharing import sharing_bp
from routes.intelligence import intelligence_bp
from services.firebase_service import initialize_demo_data
from datetime import datetime, timezone

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/intellidoc.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('IntelliDoc startup')

    # Make datetime.now available to all templates
    @app.context_processor
    def inject_now():
        return {'now': lambda: datetime.now(timezone.utc)}

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(folders_bp, url_prefix='/folders')
    app.register_blueprint(sharing_bp, url_prefix='/sharing')
    app.register_blueprint(intelligence_bp, url_prefix='/intelligence')

    @app.route('/')
    def index():
        return render_template('index.html', title='Overview - IntelliDoc')

    # Initialize demo data for presentation
    initialize_demo_data()

    return app

# Create global app instance for gunicorn compatibility
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
