from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class SuggestionService:
    def __init__(self):
        from services.document_service import DocumentService
        self.doc_service = DocumentService()

    def get_inbox_items(self, user_id: str):
        """
        Retrieves all documents for a user that have pending suggestions.
        """
        docs = self.doc_service.list_documents_by_owner(user_id)
        # Filter docs that have suggestions_status == 'pending' and actually have some suggested fields
        pending_docs = [
            doc for doc in docs 
            if getattr(doc, 'suggestions_status', '') == 'pending' and
            (getattr(doc, 'suggested_title', None) or getattr(doc, 'suggested_folder_id', None) or getattr(doc, 'suggested_tags', None))
        ]
        return pending_docs

    def accept_suggestions(self, doc_id: str, user_id: str, accepted_fields: dict) -> bool:
        """
        Accepts specific AI suggestions.
        accepted_fields is a dict like {'title': True, 'tags': False, 'folder_id': True}
        """
        doc = self.doc_service.get_document(doc_id)
        if not doc or doc.owner_id != user_id:
            return False

        updates = {}
        
        if accepted_fields.get('title') and doc.suggested_title:
            updates['title'] = doc.suggested_title
        if accepted_fields.get('tags') and doc.suggested_tags:
            # Merge tags
            current_tags = set(doc.tags or [])
            new_tags = set(doc.suggested_tags or [])
            updates['tags'] = list(current_tags.union(new_tags))
        if accepted_fields.get('folder_id') and doc.suggested_folder_id:
            updates['folder_id'] = doc.suggested_folder_id

        # Mark suggestions as processed
        updates['suggestions_status'] = 'accepted'
        updates['UpdatedAt'] = datetime.now(timezone.utc)
        
        return self.doc_service.update_document(doc_id, updates)

    def reject_suggestions(self, doc_id: str, user_id: str) -> bool:
        """
        Rejects all pending AI suggestions for a document.
        """
        doc = self.doc_service.get_document(doc_id)
        if not doc or doc.owner_id != user_id:
            return False
            
        updates = {
            'suggestions_status': 'rejected',
            'UpdatedAt': datetime.now(timezone.utc)
        }
        return self.doc_service.update_document(doc_id, updates)
