import os
# Clear any existing Firebase-related env vars for a clean test
for key in list(os.environ.keys()):
    if key.startswith('FIREBASE_') or key == 'FLASK_SECRET_KEY':
        del os.environ[key]

# Now set only the Firebase config we want to test
os.environ['FIREBASE_PROJECT_ID'] = 'test-project'
os.environ['FIREBASE_CLIENT_EMAIL'] = 'test@test-project.iam.gserviceaccount.com'
os.environ['FIREBASE_PRIVATE_KEY'] = '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDdummy\n-----END PRIVATE KEY-----'
# Intentionally NOT setting FIREBASE_STORAGE_BUCKET

# Now import config after setting environment
import importlib
import sys
# Remove config from sys.modules if it's already loaded
if 'config' in sys.modules:
    del sys.modules['config']
if 'services.firebase_service' in sys.modules:
    del sys.modules['services.firebase_service']

from config import Config
print("Config values after setting environment:")
print(f"FIREBASE_PROJECT_ID: {Config.FIREBASE_PROJECT_ID}")
print(f"FIREBASE_CLIENT_EMAIL: {Config.FIREBASE_CLIENT_EMAIL}")
print(f"FIREBASE_STORAGE_BUCKET: {repr(Config.FIREBASE_STORAGE_BUCKET)}")

# Try to initialize Firebase
import firebase_admin
from firebase_admin import credentials

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": Config.FIREBASE_PROJECT_ID,
            "private_key_id": Config.FIREBASE_PRIVATE_KEY_ID or "",
            "private_key": (Config.FIREBASE_PRIVATE_KEY or "").strip().replace('\\n', '\n'),
            "client_email": Config.FIREBASE_CLIENT_EMAIL,
            "client_id": Config.FIREBASE_CLIENT_ID or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{Config.FIREBASE_CLIENT_EMAIL.replace('@', '%40')}" if Config.FIREBASE_CLIENT_EMAIL else ""
        })
        options = {}
        if Config.FIREBASE_STORAGE_BUCKET:
            options['storageBucket'] = Config.FIREBASE_STORAGE_BUCKET
        print(f"Firebase options: {options}")
        firebase_app = firebase_admin.initialize_app(cred, options)
        print(f"Firebase initialized successfully with app: {firebase_app}")
        _firebase_initialized = True
    else:
        firebase_app = firebase_admin.get_app()
        print(f"Firebase already initialized with app: {firebase_app}")
        _firebase_initialized = True

    # Try to get storage bucket - this is where the error occurs
    from firebase_admin import storage
    if Config.FIREBASE_STORAGE_BUCKET:
        bucket = storage.bucket(Config.FIREBASE_STORAGE_BUCKET)
        print(f"Storage bucket retrieved with explicit name: {bucket}")
    else:
        print("ERROR: FIREBASE_STORAGE_BUCKET is not configured")
        print("Firebase Storage bucket name is required for document storage functionality.")
        # Don't call storage.bucket() without args as it will fail
        # Instead, show what the proper error should be
        print("To fix this, set the FIREBASE_STORAGE_BUCKET environment variable")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()