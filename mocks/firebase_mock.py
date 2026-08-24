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

    def offset(self, offset_val):
        # For simplicity, we'll ignore offset in mock
        # In a more advanced mock, we could store the offset
        return self

    def order_by(self, field, direction=None):
        # For simplicity, we'll ignore order_by in mock
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

    def generate_signed_url(self, method, expiration, headers=None):
        # Return a mock signed URL
        return f"https://storage.mock/{self.path}?signed=true"

    def delete(self):
        # Mock delete
        if self.path in self.objects:
            del self.objects[self.path]