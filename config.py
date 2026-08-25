import os
from dotenv import load_dotenv
import logging

load_dotenv()  # Load environment variables from .env

class Config:
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        if DEBUG:
            SECRET_KEY = 'dev-secret-key-change-me'
            logging.warning('Using default SECRET_KEY for development. Set FLASK_SECRET_KEY in production.')
        else:
            raise RuntimeError('SECRET_KEY must be set in production environment.')

    # Firebase configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY')
    FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')

    # Other settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit

    # Session cookie settings
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
