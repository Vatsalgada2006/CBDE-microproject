from services.firebase_service import firestore_db
from models.share import Share
from datetime import datetime, timezone
from typing import Optional, List

class ShareService:
    def __init__(self):
        self.db = firestore_db
        self.collection = self.db.collection('shares')

    def create_share(self, share: Share) -> Share:
        """Create a new share."""
        if share.share_id is None:
            share_ref = self.collection.document()
            share.share_id = share_ref.id
        else:
            share_ref = self.collection.document(share.share_id)
        share.CreatedAt = datetime.now(timezone.utc)
        share_ref.set(share.to_dict())
        return share

    def get_share(self, share_id: str) -> Optional[Share]:
        """Get a share by its ID."""
        share_ref = self.collection.document(share_id)
        share_snapshot = share_ref.get()
        if share_snapshot.exists:
            return Share.from_dict(share_snapshot.to_dict())
        return None

    def update_share(self, share: Share) -> Share:
        """Update an existing share."""
        if not share.share_id:
            raise ValueError("Share ID is required for update")
        share.CreatedAt = datetime.now(timezone.utc)
        share_ref = self.collection.document(share.share_id)
        share_ref.update(share.to_dict())
        return share

    def delete_share(self, share_id: str) -> None:
        """Delete a share by its ID."""
        self.collection.document(share_id).delete()

    def list_shares_by_owner(self, owner_id: str, limit: int = 50) -> List[Share]:
        """List shares where the user is the owner."""
        shares = []
        query = self.collection.where('owner_id', '==', owner_id).limit(limit)
        for share in query.stream():
            shares.append(Share.from_dict(share.to_dict()))
        return shares

    def list_shares_shared_with(self, shared_with_id: str, limit: int = 50) -> List[Share]:
        """List shares shared with a given user."""
        shares = []
        query = self.collection.where('shared_with_id', '==', shared_with_id).limit(limit)
        for share in query.stream():
            shares.append(Share.from_dict(share.to_dict()))
        return shares

    def get_share_for_document_and_user(self, document_id: str, user_id: str) -> Optional[Share]:
        """Get a share record for a specific document and user (where the user is the one with whom it's shared)."""
        try:
            query = self.collection.where('document_id', '==', document_id).where('shared_with_id', '==', user_id).limit(1)
            for share in query.stream():
                return Share.from_dict(share.to_dict())
        except Exception as e:
            return None
        return None