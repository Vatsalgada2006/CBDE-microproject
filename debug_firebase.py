import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

print("Environment variables:")
print(f"FIREBASE_PROJECT_ID: {os.environ.get('FIREBASE_PROJECT_ID')}")
print(f"FIREBASE_CLIENT_EMAIL: {os.environ.get('FIREBASE_CLIENT_EMAIL')}")
print(f"FIREBASE_STORAGE_BUCKET: {os.environ.get('FIREBASE_STORAGE_BUCKET')}")
print(f"FIREBASE_PRIVATE_KEY: {os.environ.get('FIREBASE_PRIVATE_KEY')[:50]}..." if os.environ.get('FIREBASE_PRIVATE_KEY') else "FIREBASE_PRIVATE_KEY: None")

# Now let's check the config
from config import Config
print("\nConfig values:")
print(f"FIREBASE_PROJECT_ID: {Config.FIREBASE_PROJECT_ID}")
print(f"FIREBASE_CLIENT_EMAIL: {Config.FIREBASE_CLIENT_EMAIL}")
print(f"FIREBASE_STORAGE_BUCKET: {Config.FIREBASE_STORAGE_BUCKET}")
print(f"FIREBASE_PRIVATE_KEY: {Config.FIREBASE_PRIVATE_KEY[:50]}..." if Config.FIREBASE_PRIVATE_KEY else "FIREBASE_PRIVATE_KEY: None")

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
        firebase_app = firebase_admin.initialize_app(cred, options)
        print(f"\nFirebase initialized successfully with app: {firebase_app}")
        print(f"Storage bucket option: {options.get('storageBucket', 'Not set')}")
    else:
        firebase_app = firebase_admin.get_app()
        print(f"\nFirebase already initialized with app: {firebase_app}")

    # Try to get storage bucket
    from firebase_admin import storage
    if Config.FIREBASE_STORAGE_BUCKET:
        bucket = storage.bucket(Config.FIREBASE_STORAGE_BUCKET)
        print(f"Storage bucket retrieved with explicit name: {bucket}")
    else:
        print("ERROR: FIREBASE_STORAGE_BUCKET is not configured")
        print("Firebase Storage bucket name is required for document storage functionality.")
        # Demonstrate what the error would be:
        try:
            bucket = storage.bucket()  # This will fail if no default bucket set
            print(f"Storage bucket retrieved without explicit name: {bucket}")
        except Exception as e:
            print(f"Calling storage.bucket() without arguments fails with: {e}")

except Exception as e:
    print(f"\nError initializing Firebase: {e}")
    import traceback
    traceback.print_exc()