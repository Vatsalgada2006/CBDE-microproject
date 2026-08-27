from flask import jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
import time
from flask import Flask, render_template, request, g
from config import Config
from routes.auth import auth_bp
from routes.documents import documents_bp
from routes.folders import folders_bp
from routes.sharing import sharing_bp
from routes.intelligence import intelligence_bp
from services.firebase_service import initialize_demo_data
from datetime import datetime, timezone

# In-memory store for rate limiting (in production, use Redis or similar)
_request_counts = {}

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

    # Security headers
    @app.after_request
    def add_security_headers(response):
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://www.gstatic.com https://www.google.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.googleapis.com https://*.google.com https://www.gstatic.com; "
            "frame-src 'self' https://accounts.google.com;"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Remove server header (optional)
        # response.headers['Server'] = 'IntelliDoc'
        
        return response

    # Rate limiting
    def is_rate_limited(key, limit=10, window=60):
        """Basic rate limiting: limit requests per window (in seconds)"""
        now = time.time()
        window_start = now - window
        
        # Prevent memory exhaustion by periodically cleaning the entire dict
        if len(_request_counts) > 1000:
            expired_keys = [k for k, v in _request_counts.items() if not v or max(v) < window_start]
            for k in expired_keys:
                _request_counts.pop(k, None)

        # Clean old entries
        if key in _request_counts:
            _request_counts[key] = [t for t in _request_counts[key] if t > window_start]
        else:
            _request_counts[key] = []
        
        # Check if limit exceeded
        if len(_request_counts[key]) >= limit:
            return True
        
        # Add current request
        _request_counts[key].append(now)
        return False

    @app.before_request
    def check_rate_limit():
        # Apply rate limiting to auth endpoints
        if request.path.startswith('/auth/'):
            # Use IP address as key (in production, consider user ID or API key)
            key = f"rate_limit:{request.remote_addr}:{request.path}"
            if is_rate_limited(key, limit=20, window=60):  # 20 requests per minute
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(folders_bp, url_prefix='/folders')
    app.register_blueprint(sharing_bp, url_prefix='/sharing')
    app.register_blueprint(intelligence_bp, url_prefix='/intelligence')

    @app.route('/')
    def index():
        return render_template('index.html', title='Overview - IntelliDoc')

    @app.route('/inbox')
    def inbox():
        return render_template('inbox.html', title='AI Inbox - IntelliDoc')

    @app.route('/health', methods=['GET'])
    def health_check():
        from services.health_service import HealthService
        health_service = HealthService()
        health_data = health_service.check_all()
        
        # Add basic environment info
        health_data['environment'] = app.config.get('ENV')
        
        # Determine HTTP status code based on health
        status_code = 200
        if health_data.get('status') == 'unhealthy':
            status_code = 503
            
        return jsonify(health_data), status_code

    # Initialize demo data for presentation in development/mock mode only
    if app.config.get('DEBUG') or os.environ.get('USE_MOCK_FIREBASE') == 'true':
        try:
            initialize_demo_data()
        except Exception as e:
            app.logger.warning(f"Could not initialize demo data: {e}")

    return app

# Create global app instance for gunicorn compatibility
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
