from datetime import datetime, timezone
from typing import Optional, List

class Document:
    def __init__(self, doc_id=None, owner_id=None, filename=None, content_type=None,
                 size=0, storage_path=None, CreatedAt=None, UpdatedAt=None,
                 folder_id=None, tags=None, extraction_status="pending",
                 intelligence_status="pending", hash=None, version=1,
                 embedding: Optional[List[float]] = None, is_favorite=False):
        self.doc_id = doc_id
        self.owner_id = owner_id
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.storage_path = storage_path
        self.CreatedAt = CreatedAt or datetime.now(timezone.utc)
        self.UpdatedAt = UpdatedAt or datetime.now(timezone.utc)
        self.folder_id = folder_id
        self.tags = tags or []  # list of tags associated with the document
        self.extraction_status = extraction_status  # pending, processing, completed, failed
        self.intelligence_status = intelligence_status  # pending, processing, completed, failed
        self.hash = hash  # hash of the file for duplicate detection
        self.version = version  # version number for versioning
        self.embedding = embedding  # list of floats representing the document embedding
        self.is_favorite = is_favorite  # whether the document is marked as favorite
    
    def to_dict(self):
        return {
            'doc_id': self.doc_id,
            'owner_id': self.owner_id,
            'filename': self.filename,
            'content_type': self.content_type,
            'size': self.size,
            'storage_path': self.storage_path,
            'CreatedAt': self.CreatedAt,
            'UpdatedAt': self.UpdatedAt,
            'folder_id': self.folder_id,
            'tags': self.tags,
            'extraction_status': self.extraction_status,
            'intelligence_status': self.intelligence_status,
            'hash': self.hash,
            'version': self.version,
            'embedding': self.embedding,
            'is_favorite': self.is_favorite
        }
    
    @staticmethod
    def from_dict(data):
        return Document(
            doc_id=data.get('doc_id'),
            owner_id=data.get('owner_id'),
            filename=data.get('filename'),
            content_type=data.get('content_type'),
            size=data.get('size'),
            storage_path=data.get('storage_path'),
            CreatedAt=data.get('CreatedAt'),
            UpdatedAt=data.get('UpdatedAt'),
            folder_id=data.get('folder_id'),
            tags=data.get('tags'),
            extraction_status=data.get('extraction_status'),
            intelligence_status=data.get('intelligence_status'),
            hash=data.get('hash'),
            version=data.get('version'),
            embedding=data.get('embedding'),
            is_favorite=data.get('is_favorite', False)
        )
