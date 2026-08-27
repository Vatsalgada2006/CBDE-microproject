import logging
from firebase_admin import firestore
from services.firebase_service import firestore_db
from models.document import Document
from typing import List, Optional, Dict
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.db = firestore_db
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
            logger.error(f"Error listing documents: {e}")
        return docs

    def list_documents_by_owner_with_filters(self, owner_id: str, search_query: str = '', file_type: str = 'all', sort_by: str = 'date_desc', page: int = 1, limit: int = 12, folder_id: Optional[str] = None) -> Dict:
        """
        List documents for a given owner with filtering, sorting, and pagination.
        """
        try:
            # Start with base query
            query = self.collection.where('owner_id', '==', owner_id)

            # Apply folder filter if provided
            if folder_id is not None:
                query = query.where('folder_id', '==', folder_id)

            # Apply search filter if provided
            # Firestore prefix range: >= search_query AND <= search_query + '\uf8ff'
            # '\uf8ff' is a high Unicode char that sorts after most regular characters,
            # giving us a case-sensitive prefix search on the filename field.
            if search_query:
                query = query.where('filename', '>=', search_query).where('filename', '<=', search_query + '\uf8ff')

            # Apply file type filter if provided
            if file_type != 'all':
                if file_type == 'pdf':
                    query = query.where('content_type', '==', 'application/pdf')
                elif file_type == 'doc':
                    query = query.where('content_type', 'in', [
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    ])
                elif file_type == 'spreadsheet':
                    query = query.where('content_type', 'in', [
                        'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    ])
                elif file_type == 'presentation':
                    query = query.where('content_type', 'in', [
                        'application/vnd.ms-powerpoint',
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    ])
                elif file_type == 'image':
                    query = query.where('content_type', '>=', 'image/').where('content_type', '<=', 'image/\uf8ff')
                elif file_type == 'text':
                    query = query.where('content_type', '>=', 'text/').where('content_type', '<=', 'text/\uf8ff')

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

            # Fetch all matching results for count, then slice for pagination.
            # For production-scale datasets, maintain a counter or use Firestore
            # aggregation queries instead.
            all_results = list(query.stream())
            total_docs = len(all_results)
            total_pages = math.ceil(total_docs / limit) if total_docs > 0 else 1

            # Slice for page
            start = (page - 1) * limit
            page_results = all_results[start:start + limit]

            docs = [Document.from_dict(snap.to_dict()) for snap in page_results]

            return {
                'documents': docs,
                'pagination': {
                    'page': page,
                    'pages': total_pages,
                    'total': total_docs
                }
            }
        except Exception as e:
            logger.error(f"Error listing documents with filters: {e}")
            return {
                'documents': [],
                'pagination': {
                    'page': page,
                    'pages': 0,
                    'total': 0
                }
            }

    def list_documents_by_folder(self, folder_id: str) -> List[Document]:
        """
        List all documents in a given folder.
        """
        docs = []
        try:
            query = self.collection.where('folder_id', '==', folder_id)
            for doc in query.stream():
                docs.append(Document.from_dict(doc.to_dict()))
        except Exception as e:
            logger.error(f"Error listing documents by folder: {e}")
        return docs

    # ------------------------------------------------------------------ #
    #  New methods added in Phase 3                                       #
    # ------------------------------------------------------------------ #

    def get_documents_by_ids(self, doc_ids: List[str]) -> List[Document]:
        """
        Batch-fetch documents by a list of IDs.  Firestore doesn't have a
        native 'WHERE id IN [...]' that works across arbitrary-length lists,
        so we fetch individually and skip missing docs.
        """
        docs = []
        for doc_id in doc_ids:
            try:
                snap = self.collection.document(doc_id).get()
                if snap.exists:
                    docs.append(Document.from_dict(snap.to_dict()))
            except Exception as e:
                logger.warning(f"Error fetching document {doc_id}: {e}")
        return docs

    def list_shared_documents(self, user_id: str) -> List[Document]:
        """
        Return documents that have been shared with *user_id*.
        Requires a ShareService lookup to discover the document IDs first,
        then batch-fetches the documents.
        """
        try:
            from services.share_service import ShareService
            share_svc = ShareService()
            shares = share_svc.list_shares_shared_with(user_id)
            doc_ids = list({s.document_id for s in shares if s.document_id})
            return self.get_documents_by_ids(doc_ids)
        except Exception as e:
            logger.error(f"Error listing shared documents for {user_id}: {e}")
            return []

    def search_documents(self, owner_id: str, query_text: str, limit: int = 20) -> List[Document]:
        """
        Case-insensitive client-side search across filename, title, tags,
        and entities.  For small-to-medium libraries this is adequate;
        for larger datasets integrate Algolia / Typesense.
        """
        try:
            all_docs = self.list_documents_by_owner(owner_id)
            query_lower = query_text.lower()
            matches = []
            for doc in all_docs:
                searchable = ' '.join(filter(None, [
                    doc.filename,
                    getattr(doc, 'title', None),
                    ' '.join(doc.tags) if doc.tags else None,
                    ' '.join(getattr(doc, 'entities', None) or []),
                    getattr(doc, 'document_type', None),
                ]))
                if query_lower in searchable.lower():
                    matches.append(doc)
                    if len(matches) >= limit:
                        break
            return matches
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []