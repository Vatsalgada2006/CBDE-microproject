import logging
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
import uuid
from datetime import datetime, timezone
from config import Config

logger = logging.getLogger(__name__)

# Import mock classes when Firebase is not initialized
from mocks.firebase_mock import MockAuth, MockFirestore, MockStorageBucket


# Flag to track if Firebase is initialized
_firebase_initialized = False
firebase_app = None

def initialize_firebase():
    global _firebase_initialized, firebase_app
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
            _firebase_initialized = True
        else:
            firebase_app = firebase_admin.get_app()
            _firebase_initialized = True
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin SDK: {e}")
        _firebase_initialized = False
        firebase_app = None

# Initialize Firebase when this module is loaded
initialize_firebase()


# If Firebase is not initialized, replace the auth module with our mock
if not _firebase_initialized:
    logger.info(f"Firebase not initialized (_firebase_initialized={_firebase_initialized}), replacing auth with mock")
    auth = MockAuth()
else:
    logger.info(f"Firebase initialized (_firebase_initialized={_firebase_initialized})")

# Initialize Firestore and Storage clients or mocks
if _firebase_initialized:
    firestore_db = firestore.client(firebase_app)
    if Config.FIREBASE_STORAGE_BUCKET:
        storage_bucket = storage.bucket(Config.FIREBASE_STORAGE_BUCKET)
    else:
        # Firebase is initialized but storage bucket is not configured
        # This is a configuration error - storage is required for document management
        raise ValueError(
            "FIREBASE_STORAGE_BUCKET environment variable is not set. "
            "Firebase Storage bucket name is required for document storage functionality."
        )
else:
    firestore_db = MockFirestore()
    storage_bucket = MockStorageBucket()

def initialize_demo_data():
    """Initialize demo data for presentation purposes when using mock Firebase."""
    # Only initialize demo data if we're using mock Firebase
    if _firebase_initialized:
        return  # Skip demo data initialization if using real Firebase

    try:
        # Import Document model
        from models.document import Document

        # Create sample documents
        sample_docs = [
            {
                "filename": "sample_contract.pdf",
                "content_type": "application/pdf",
                "size": 102400,  # 100KB
                "storage_path": "uploads/sample_contract.pdf",
                "hash": "a" * 64,  # dummy hash
                "extraction_status": "completed",
                "intelligence_status": "completed",
                "embedding": [0.1] * 384,  # dummy embedding (384 dims for all-MiniLM-L6-v2)
                "CreatedAt": datetime.now(timezone.utc),
                "UpdatedAt": datetime.now(timezone.utc)
            },
            {
                "filename": "project_proposal.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size": 204800,  # 200KB
                "storage_path": "uploads/project_proposal.docx",
                "hash": "b" * 64,  # dummy hash
                "extraction_status": "completed",
                "intelligence_status": "completed",
                "embedding": [0.2] * 384,  # dummy embedding
                "CreatedAt": datetime.now(timezone.utc),
                "UpdatedAt": datetime.now(timezone.utc)
            },
            {
                "filename": "meeting_notes.txt",
                "content_type": "text/plain",
                "size": 5120,  # 5KB
                "storage_path": "uploads/meeting_notes.txt",
                "hash": "c" * 64,  # dummy hash
                "extraction_status": "completed",
                "intelligence_status": "completed",
                "embedding": [0.3] * 384,  # dummy embedding
                "CreatedAt": datetime.now(timezone.utc),
                "UpdatedAt": datetime.now(timezone.utc)
            }
        ]

        # Insert sample documents
        for i, doc_data in enumerate(sample_docs):
            # Create document object
            document = Document(
                owner_id="mock_uid",
                filename=doc_data["filename"],
                content_type=doc_data["content_type"],
                size=doc_data["size"],
                storage_path=doc_data["storage_path"],
                hash=doc_data["hash"],
                extraction_status=doc_data["extraction_status"],
                intelligence_status=doc_data["intelligence_status"],
                CreatedAt=doc_data["CreatedAt"],
                UpdatedAt=doc_data["UpdatedAt"]
            )

            # Set embedding if provided
            if "embedding" in doc_data:
                document.embedding = doc_data["embedding"]

            # Save document
            doc_ref = firestore_db.collection('documents').document()
            document.doc_id = doc_ref.id
            doc_ref.set(document.to_dict())

            logger.info(f"Created demo document: {document.doc_id} - {document.filename}")

    except Exception as e:
        logger.error(f"Error initializing demo data: {e}")
        # Don't fail the app initialization if demo data fails
def verify_firebase_token(id_token):
    if not _firebase_initialized:
        # Return a mock decoded token for development
        return {
            'uid': 'mock_uid',
            'email': 'mock@example.com',
            'name': 'Mock User',
            'picture': ''
        }
    try:
        # Verify the ID token while checking if the token is revoked.
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return None
