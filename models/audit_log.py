from datetime import datetime, timezone
from typing import Optional

class AuditLog:
    def __init__(self, log_id: Optional[str] = None, user_id: Optional[str] = None,
                 action: Optional[str] = None, resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None, details: Optional[str] = None,
                 ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.log_id = log_id
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data):
        return AuditLog(
            log_id=data.get('log_id'),
            user_id=data.get('user_id'),
            action=data.get('action'),
            resource_type=data.get('resource_type'),
            resource_id=data.get('resource_id'),
            details=data.get('details'),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            created_at=data.get('created_at')
        )
