from flask import Flask, render_template
from config import Config
from routes.auth import auth_bp
from routes.documents import documents_bp
from routes.folders import folders_bp
from routes.sharing import sharing_bp
from routes.intelligence import intelligence_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(folders_bp, url_prefix='/folders')
    app.register_blueprint(sharing_bp, url_prefix='/sharing')
    app.register_blueprint(intelligence_bp, url_prefix='/intelligence')

    @app.route('/')
    def index():
        return render_template('base.html', title='Home')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
