from datetime import datetime, timezone
from typing import Optional

class Relationship:
    def __init__(self, relationship_id: Optional[str] = None, source_document_id: Optional[str] = None,
                 target_document_id: Optional[str] = None, relationship_type: Optional[str] = None,
                 confidence: float = 0.0, reason: Optional[str] = None,
                 CreatedAt: Optional[datetime] = None):
        self.relationship_id = relationship_id
        self.source_document_id = source_document_id
        self.target_document_id = target_document_id
        self.relationship_type = relationship_type  # e.g., 'related', 'possible_duplicate', 'possible_previous_version', etc.
        self.confidence = confidence
        self.reason = reason
        self.CreatedAt = CreatedAt or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'relationship_id': self.relationship_id,
            'source_document_id': self.source_document_id,
            'target_document_id': self.target_document_id,
            'relationship_type': self.relationship_type,
            'confidence': self.confidence,
            'reason': self.reason,
            'CreatedAt': self.CreatedAt
        }

    @staticmethod
    def from_dict(data):
        return Relationship(
            relationship_id=data.get('relationship_id'),
            source_document_id=data.get('source_document_id'),
            target_document_id=data.get('target_document_id'),
            relationship_type=data.get('relationship_type'),
            confidence=data.get('confidence'),
            reason=data.get('reason'),
            CreatedAt=data.get('CreatedAt')
        )