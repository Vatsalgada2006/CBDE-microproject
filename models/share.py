from datetime import datetime, timezone
from typing import Optional

class Share:
    def __init__(self, share_id: Optional[str] = None, document_id: Optional[str] = None,
                 owner_id: Optional[str] = None, shared_with_id: Optional[str] = None,
                 permission: Optional[str] = None,  # deprecated in favor of 'role'
                 CreatedAt: Optional[datetime] = None,
                 shared_with_email: Optional[str] = None,
                 role: str = 'viewer',
                 expires_at: Optional[datetime] = None,
                 is_link_share: bool = False,
                 share_link_token: Optional[str] = None,
                 message: Optional[str] = None,
                 accepted: bool = False):
        self.share_id = share_id
        self.document_id = document_id
        self.owner_id = owner_id
        self.shared_with_id = shared_with_id  # The user ID with whom the document is shared
        self.permission = permission
        self.CreatedAt = CreatedAt or datetime.now(timezone.utc)
        self.shared_with_email = shared_with_email
        self.role = role
        self.expires_at = expires_at
        self.is_link_share = is_link_share
        self.share_link_token = share_link_token
        self.message = message
        self.accepted = accepted

    def to_dict(self):
        return {
            'share_id': self.share_id,
            'document_id': self.document_id,
            'owner_id': self.owner_id,
            'shared_with_id': self.shared_with_id,
            'permission': self.permission,
            'CreatedAt': self.CreatedAt,
            'shared_with_email': self.shared_with_email,
            'role': self.role,
            'expires_at': self.expires_at,
            'is_link_share': self.is_link_share,
            'share_link_token': self.share_link_token,
            'message': self.message,
            'accepted': self.accepted
        }

    @staticmethod
    def from_dict(data):
        return Share(
            share_id=data.get('share_id'),
            document_id=data.get('document_id'),
            owner_id=data.get('owner_id'),
            shared_with_id=data.get('shared_with_id'),
            permission=data.get('permission'),
            CreatedAt=data.get('CreatedAt'),
            shared_with_email=data.get('shared_with_email'),
            role=data.get('role', 'viewer'),
            expires_at=data.get('expires_at'),
            is_link_share=data.get('is_link_share', False),
            share_link_token=data.get('share_link_token'),
            message=data.get('message'),
            accepted=data.get('accepted', False)
        )