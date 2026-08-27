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
    """Mock Firestore collection with query-builder support."""

    def __init__(self, name):
        self.name = name
        self.documents = {}  # document_id -> MockDocument

    def document(self, document_id=None):
        if document_id is None:
            import uuid
            document_id = str(uuid.uuid4())
        if document_id not in self.documents:
            self.documents[document_id] = MockDocument(document_id)
        return self.documents[document_id]

    # Query-builder entry points — return a MockQuery so filters never
    # mutate the collection itself (avoids cross-query contamination).
    def where(self, field, op, value):
        return MockQuery(self).where(field, op, value)

    def order_by(self, field, direction=None):
        return MockQuery(self).order_by(field, direction)

    def limit(self, limit_val):
        return MockQuery(self).limit(limit_val)

    def offset(self, offset_val):
        return MockQuery(self).offset(offset_val)

    def stream(self):
        """Unfiltered stream — returns every document with data."""
        return MockQuery(self).stream()


class MockQuery:
    """Accumulates where / order_by / limit / offset clauses and applies
    them when stream() is called — mirrors the real Firestore Query API."""

    def __init__(self, collection):
        self._collection = collection
        self._filters = []
        self._orders = []
        self._limit = None
        self._offset = 0

    # -- chainable builder methods ----------------------------------------

    def where(self, field, op, value):
        self._filters.append((field, op, value))
        return self

    def order_by(self, field, direction=None):
        self._orders.append((field, direction))
        return self

    def limit(self, limit_val):
        self._limit = limit_val
        return self

    def offset(self, offset_val):
        self._offset = offset_val
        return self

    # -- execution --------------------------------------------------------

    def stream(self):
        from types import SimpleNamespace

        # 1. Collect documents that have data
        candidates = [
            (doc_id, doc)
            for doc_id, doc in self._collection.documents.items()
            if doc.data
        ]

        # 2. Apply filters
        for field, op, value in self._filters:
            filtered = []
            for doc_id, doc in candidates:
                doc_val = doc.data.get(field)
                if op == '==':
                    if doc_val == value:
                        filtered.append((doc_id, doc))
                elif op == '!=':
                    if doc_val != value:
                        filtered.append((doc_id, doc))
                elif op == '>=':
                    if doc_val is not None and doc_val >= value:
                        filtered.append((doc_id, doc))
                elif op == '<=':
                    if doc_val is not None and doc_val <= value:
                        filtered.append((doc_id, doc))
                elif op == '>':
                    if doc_val is not None and doc_val > value:
                        filtered.append((doc_id, doc))
                elif op == '<':
                    if doc_val is not None and doc_val < value:
                        filtered.append((doc_id, doc))
                elif op == 'in':
                    if doc_val in value:
                        filtered.append((doc_id, doc))
                elif op == 'array_contains':
                    if isinstance(doc_val, list) and value in doc_val:
                        filtered.append((doc_id, doc))
                else:
                    # Unknown operator — include the doc (lenient)
                    filtered.append((doc_id, doc))
            candidates = filtered

        # 3. Apply ordering
        for field, direction in reversed(self._orders):
            desc = False
            if direction is not None:
                # Handle firestore.Query.DESCENDING (int 2) or string
                if isinstance(direction, int):
                    desc = direction != 1  # ASCENDING = 1
                elif hasattr(direction, 'name'):
                    desc = direction.name == 'DESCENDING'
                elif isinstance(direction, str):
                    desc = 'desc' in direction.lower()
            candidates.sort(
                key=lambda pair: pair[1].data.get(field) or '',
                reverse=desc,
            )

        # 4. Apply offset & limit
        if self._offset:
            candidates = candidates[self._offset:]
        if self._limit is not None:
            candidates = candidates[:self._limit]

        # 5. Build snapshots
        snapshots = []
        for doc_id, doc in candidates:
            snap = SimpleNamespace()
            snap.exists = True
            snap.to_dict = (lambda d=doc.data: d)
            snap.id = doc_id
            snapshots.append(snap)
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
            self.objects[path] = MockBlob(path, self)
        return self.objects[path]


class MockBlob:
    def __init__(self, path, bucket=None):
        self.path = path
        self.bucket = bucket
        self.content = None

    def upload_from_string(self, data, content_type=None):
        self.content = data

    def upload_from_file(self, file_obj):
        file_obj.seek(0)
        self.content = file_obj.read()

    def download_as_string(self):
        return self.content or b""

    def generate_signed_url(self, expiration=None, method='GET', **kwargs):
        # Return a mock signed URL
        return f"https://storage.mock/{self.path}?signed=true"

    def delete(self):
        # Mock delete
        if self.bucket and self.path in self.bucket.objects:
            del self.bucket.objects[self.path]