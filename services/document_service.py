from firebase_admin import firestore
from services.firebase_service import _firebase_initialized, firestore_db
from models.document import Document
from typing import List, Optional, Dict
import math
from datetime import datetime, timezone

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

    def to_dict(self):
        return self.data

    def get(self):
        from types import SimpleNamespace
        mock_doc = SimpleNamespace()
        mock_doc.exists = bool(self.data)
        mock_doc.to_dict = lambda: self.data
        return mock_doc

    def delete(self):
        # Mock delete
        self.data = {}

class DocumentService:
    def __init__(self):
        # Use mock Firestore if Firebase is not initialized
        if _firebase_initialized:
            self.db = firestore_db
            self.collection = self.db.collection('documents')
        else:
            self.db = MockFirestore()
            self.collection = self.db.collection('documents')

    def create_document(self, document: Document) -> Document:
        """
        Create a new document in Firestore.
        """
        doc_ref = self.collection.document()
        document.doc_id = doc_ref.id
        doc_ref.set(document.to_dict())
        return document

    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        """
        doc_ref = self.collection.document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return Document.from_dict(doc.to_dict())
        return None

    def update_document(self, document: Document) -> Document:
        """
        Update an existing document.
        """
        document.UpdatedAt = datetime.now(timezone.utc)
        doc_ref = self.collection.document(document.doc_id)
        doc_ref.update(document.to_dict())
        return document

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        """
        try:
            self.collection.document(doc_id).delete()
            return True
        except Exception:
            return False

    def list_documents_by_owner(self, owner_id: str) -> List[Document]:
        """
        List all documents for a given owner.
        """
        docs = []
        try:
            query = self.collection.where('owner_id', '==', owner_id)
            for doc in query.stream():
                docs.append(Document.from_dict(doc.to_dict()))
        except Exception as e:
            print(f"Error listing documents: {e}")
        return docs

    def list_documents_by_owner_with_filters(self, owner_id: str, search_query: str = '', file_type: str = 'all', sort_by: str = 'date_desc', page: int = 1, limit: int = 12) -> Dict:
        """
        List documents for a given owner with filtering, sorting, and pagination.
        """
        try:
            # Start with base query
            query = self.collection.where('owner_id', '==', owner_id)

            # Apply search filter if provided
            if search_query:
                # Note: Firestore doesn't support full-text search natively
                # This is a simplified implementation - in a real app, you'd use Algolia or similar
                # For now, we'll filter by filename only
                query = query.where('filename', '>=', search_query).where('filename', '<=', search_query + '')

            # Apply file type filter if provided
            if file_type != 'all':
                if file_type == 'pdf':
                    query = query.where('content_type', '==', 'application/pdf')
                elif file_type == 'doc':
                    query = query.where('content_type', 'in', [
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    ])
                elif file_type == 'image':
                    query = query.where('content_type', '>=', 'image/').where('content_type', '<', 'image/')
                elif file_type == 'text':
                    query = query.where('content_type', '>=', 'text/').where('content_type', '<', 'text/')

            # Apply sorting
            if sort_by == 'date_desc':
                query = query.order_by('CreatedAt', direction=firestore.Query.DESCENDING)
            elif sort_by == 'date_asc':
                query = query.order_by('CreatedAt', direction=firestore.Query.ASCENDING)
            elif sort_by == 'name_asc':
                query = query.order_by('filename', direction=firestore.Query.ASCENDING)
            elif sort_by == 'name_desc':
                query = query.order_by('filename', direction=firestore.Query.DESCENDING)
            elif sort_by == 'size_desc':
                query = query.order_by('size', direction=firestore.Query.DESCENDING)
            elif sort_by == 'size_asc':
                query = query.order_by('size', direction=firestore.Query.ASCENDING)

            # Get total count for pagination
            # Note: This is inefficient for large collections - in a real app, you'd maintain a count
            # Build count query by reusing the same filter logic
            count_query = self.collection.where('owner_id', '==', owner_id)

            # Apply the same filters to count query
            if search_query:
                count_query = count_query.where('filename', '>=', search_query).where('filename', '<=', search_query + '')
            if file_type != 'all':
                if file_type == 'pdf':
                    count_query = count_query.where('content_type', '==', 'application/pdf')
                elif file_type == 'doc':
                    count_query = count_query.where('content_type', 'in', [
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    ])
                elif file_type == 'image':
                    count_query = count_query.where('content_type', '>=', 'image/').where('content_type', '<', 'image/')
                elif file_type == 'text':
                    count_query = count_query.where('content_type', '>=', 'text/').where('content_type', '<', 'text/')

            # For Firestore, we need to execute the query to get count
            # In a production app with large datasets, consider maintaining a count field
            total_docs = len(list(count_query.stream()))
            total_pages = math.ceil(total_docs / limit) if total_docs > 0 else 1

            # Apply pagination
            query = query.offset((page - 1) * limit).limit(limit)

            # Execute query
            docs = []
            for doc in query.stream():
                docs.append(Document.from_dict(doc.to_dict()))

            return {
                'documents': docs,
                'pagination': {
                    'page': page,
                    'pages': total_pages,
                    'total': total_docs
                }
            }
        except Exception as e:
            print(f"Error listing documents with filters: {e}")
            return {
                'documents': [],
                'pagination': {
                    'page': page,
                    'pages': 0,
                    'total': 0
                }
            }