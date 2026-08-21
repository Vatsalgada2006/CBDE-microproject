from datetime import datetime
from typing import Optional

class Folder:
    def __init__(self, folder_id: Optional[str] = None, owner_id: Optional[str] = None,
                 name: Optional[str] = None, parent_id: Optional[str] = None,
                 CreatedAt: Optional[datetime] = None, UpdatedAt: Optional[datetime] = None):
        self.folder_id = folder_id
        self.owner_id = owner_id
        self.name = name
        self.parent_id = parent_id  # For subfolders
        self.CreatedAt = CreatedAt or datetime.utcnow()
        self.UpdatedAt = UpdatedAt or datetime.utcnow()

    def to_dict(self):
        return {
            'folder_id': self.folder_id,
            'owner_id': self.owner_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'CreatedAt': self.CreatedAt,
            'UpdatedAt': self.UpdatedAt
        }

    @staticmethod
    def from_dict(data):
        return Folder(
            folder_id=data.get('folder_id'),
            owner_id=data.get('owner_id'),
            name=data.get('name'),
            parent_id=data.get('parent_id'),
            CreatedAt=data.get('CreatedAt'),
            UpdatedAt=data.get('UpdatedAt')
        )