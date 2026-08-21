import os
import firebase_admin
from firebase_admin import credentials
import uuid
from config import Config

# Mock auth methods for when Firebase is not initialized
class MockAuth:
    @staticmethod
    def create_user(**kwargs):
        # Return a mock user record
        from types import SimpleNamespace
        user_record = SimpleNamespace()
        user_record.uid = kwargs.get('uid', 'mock_uid')
        user_record.email = kwargs.get('email', 'mock@example.com')
        user_record.display_name = kwargs.get('display_name', 'Mock User')
        user_record.email_verified = False
        user_record.disabled = False
        return user_record

    @staticmethod
    def revoke_refresh_tokens(uid):
        # Do nothing
        pass

# Mock Firestore for when Firebase is not initialized
class MockFirestore:
    def __init__(self):
        self.collections = {}
    
    def collection(self, collection_name):
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection(collection_name)
        return self.collections[collection_name]

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.documents = {}  # document_id -> MockDocument
    
    def document(self, document_id=None):
        if document_id is None:
            import uuid
            document_id = str(uuid.uuid4())
        if document_id not in self.documents:
            # Create a new MockDocument with the specified ID
            self.documents[document_id] = MockDocument(document_id)
        return self.documents[document_id]
    
    def where(self, field, op, value):
        # For simplicity, we'll ignore where in mock and return all documents
        # In a more advanced mock, we could store filters
        return self
    
    def limit(self, limit_val):
        # For simplicity, we'll ignore limit in mock
        # In a more advanced mock, we could store the limit
        return self
    
    def stream(self):
        # Return all documents as mock snapshots
        from types import SimpleNamespace
        snapshots = []
        for doc_id, doc in self.documents.items():
            mock_snapshot = SimpleNamespace()
            mock_snapshot.exists = bool(doc.data)
            mock_snapshot.to_dict = lambda d=doc.data: d
            mock_snapshot.id = doc_id
            snapshots.append(mock_snapshot)
        return snapshots

class MockDocument:
    def __init__(self, doc_id=None):
        self.data = {}
        self._id = doc_id if doc_id is not None else "mock_id_" + str(hash(str(self.data)))[:8]
    
    @property
    def id(self):
        return self._id
    
    def set(self, data):
        self.data = data
    
    def update(self, data):
        self.data.update(data)
    
    def get(self):
        from types import SimpleNamespace
        mock_doc = SimpleNamespace()
        mock_doc.exists = bool(self.data)
        mock_doc.to_dict = lambda: self.data
        return mock_doc
    
    def delete(self):
        # Mock delete
        self.data = {}

# Mock Storage for when Firebase is not initialized
class MockStorageBucket:
    def __init__(self):
        self.objects = {}
    
    def blob(self, path):
        if path not in self.objects:
            self.objects[path] = MockBlob(path)
        return self.objects[path]

class MockBlob:
    def __init__(self, path):
        self.path = path
        self.content = None
    
    def upload_from_string(self, data, content_type=None):
        self.content = data
    
    def upload_from_file(self, file_obj):
        file_obj.seek(0)
        self.content = file_obj.read()
    
    def download_as_string(self):
        return self.content or b""
    
    def generate_signed_request(self, method, expiration, headers=None):
        # Return a mock signed URL
        return f"https://storage.mock/{self.path}?signed=true"
    
    def delete(self):
        # Mock delete
        if self.path in self.objects:
            del self.objects[self.path]

# Flag to track if Firebase is initialized
_firebase_initialized = False

def initialize_firebase():
    global _firebase_initialized, firestore_db, storage_bucket
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": Config.FIREBASE_PROJECT_ID,
                "private_key_id": "",
                "private_key": Config.FIREBASE_PRIVATE_KEY.replace('\n', '\n') if Config.FIREBASE_PRIVATE_KEY else "",
                "client_email": Config.FIREBASE_CLIENT_EMAIL,
                "client_id": "",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{Config.FIREBASE_CLIENT_EMAIL.replace('@', '%40')}" if Config.FIREBASE_CLIENT_EMAIL else ""
            })
            firebase_admin.initialize_app(cred, {
                'storageBucket': Config.FIREBASE_STORAGE_BUCKET
            })
            _firebase_initialized = True
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase Admin SDK: {e}")
        _firebase_initialized = False

# Initialize Firebase when this module is loaded
initialize_firebase()

# Import auth from firebase_admin after defining MockAuth so we can replace it if needed
from firebase_admin import auth

# If Firebase is not initialized, replace the auth module with our mock
if not _firebase_initialized:
    print(f"Firebase not initialized (_firebase_initialized={_firebase_initialized}), replacing auth with mock")
    auth = MockAuth()
else:
    print(f"Firebase initialized (_firebase_initialized={_firebase_initialized})")

# Initialize Firestore and Storage clients or mocks
if _firebase_initialized:
    from firebase_admin import firestore
    firestore_db = firestore.client()
    storage_bucket = firebase_admin.storage.bucket()
else:
    firestore_db = MockFirestore()
    storage_bucket = MockStorageBucket()

# Verify Firebase ID token
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
        print(f"Error verifying Firebase token: {e}")
        return None
