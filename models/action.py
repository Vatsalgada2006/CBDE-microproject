from datetime import datetime, timezone
from typing import Optional

class Action:
    def __init__(self, action_id: Optional[str] = None, document_id: Optional[str] = None,
                 action_text: Optional[str] = None, deadline: Optional[str] = None,
                 action_type: Optional[str] = None, confidence: float = 0.0,
                 CreatedAt: Optional[datetime] = None):
        self.action_id = action_id
        self.document_id = document_id
        self.action_text = action_text
        self.deadline = deadline
        self.action_type = action_type  # 'task' or 'deadline'
        self.confidence = confidence
        self.CreatedAt = CreatedAt or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'action_id': self.action_id,
            'document_id': self.document_id,
            'action_text': self.action_text,
            'deadline': self.deadline,
            'action_type': self.action_type,
            'confidence': self.confidence,
            'CreatedAt': self.CreatedAt
        }

    @staticmethod
    def from_dict(data):
        return Action(
            action_id=data.get('action_id'),
            document_id=data.get('document_id'),
            action_text=data.get('action_text'),
            deadline=data.get('deadline'),
            action_type=data.get('action_type'),
            confidence=data.get('confidence'),
            CreatedAt=data.get('CreatedAt')
        )