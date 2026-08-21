from datetime import datetime
from typing import Optional

class Share:
    def __init__(self, share_id: Optional[str] = None, document_id: Optional[str] = None,
                 owner_id: Optional[str] = None, shared_with_id: Optional[str] = None,
                 permission: Optional[str] = None,  # 'view' or 'download'
                 CreatedAt: Optional[datetime] = None):
        self.share_id = share_id
        self.document_id = document_id
        self.owner_id = owner_id
        self.shared_with_id = shared_with_id  # The user ID with whom the document is shared
        self.permission = permission
        self.CreatedAt = CreatedAt or datetime.utcnow()

    def to_dict(self):
        return {
            'share_id': self.share_id,
            'document_id': self.document_id,
            'owner_id': self.owner_id,
            'shared_with_id': self.shared_with_id,
            'permission': self.permission,
            'CreatedAt': self.CreatedAt
        }

    @staticmethod
    def from_dict(data):
        return Share(
            share_id=data.get('share_id'),
            document_id=data.get('document_id'),
            owner_id=data.get('owner_id'),
            shared_with_id=data.get('shared_with_id'),
            permission=data.get('permission'),
            CreatedAt=data.get('CreatedAt')
        )