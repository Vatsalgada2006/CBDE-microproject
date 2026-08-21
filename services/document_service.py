from services.firebase_service import firestore_db
from models.document import Document
from datetime import datetime

class DocumentService:
    def __init__(self):
        self.db = firestore_db
        self.collection = self.db.collection('documents')
    
    def create_document(self, document: Document):
        """Create a new document record in Firestore."""
        # If doc_id is not provided, Firestore will auto-generate one
        if document.doc_id is None:
            doc_ref = self.collection.document()
            document.doc_id = doc_ref.id
        else:
            doc_ref = self.collection.document(document.doc_id)
        
        document.UpdatedAt = datetime.utcnow()
        doc_ref.set(document.to_dict())
        return document
    
    def get_document(self, doc_id):
        """Get a document by its ID."""
        doc_ref = self.collection.document(doc_id)
        doc_snapshot = doc_ref.get()
        if doc_snapshot.exists:
            return Document.from_dict(doc_snapshot.to_dict())
        return None
    
    def update_document(self, document: Document):
        """Update an existing document."""
        if not document.doc_id:
            raise ValueError("Document ID is required for update")
        document.UpdatedAt = datetime.utcnow()
        doc_ref = self.collection.document(document.doc_id)
        doc_ref.update(document.to_dict())
        return document
    
    def delete_document(self, doc_id):
        """Delete a document by its ID."""
        self.collection.document(doc_id).delete()
    
    def list_documents_by_owner(self, owner_id, limit=50):
        """List documents for a given owner."""
        docs = []
        query = self.collection.where('owner_id', '==', owner_id).limit(limit)
        for doc in query.stream():
            docs.append(Document.from_dict(doc.to_dict()))
        return docs
    
    def list_documents_by_folder(self, folder_id, limit=50):
        """List documents in a given folder."""
        docs = []
        query = self.collection.where('folder_id', '==', folder_id).limit(limit)
        for doc in query.stream():
            docs.append(Document.from_dict(doc.to_dict()))
        return docs
