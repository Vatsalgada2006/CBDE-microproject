from datetime import datetime, timezone
from typing import Optional, List

class Document:
    def __init__(self, doc_id=None, owner_id=None, filename=None, content_type=None,
                 size=0, storage_path=None, CreatedAt=None, UpdatedAt=None,
                 folder_id=None, tags=None, extraction_status="pending",
                 intelligence_status="pending", hash=None, version=1,
                 embedding: Optional[List[float]] = None, is_favorite=False,
                 llm_summary: Optional[str] = None, llm_key_points: Optional[List[str]] = None,
                 title: Optional[str] = None, document_type: Optional[str] = None,
                 classification_confidence: Optional[float] = None, starred: bool = False,
                 processing_status: str = 'pending', detected_language: Optional[str] = None,
                 page_count: Optional[int] = None, deadline_date: Optional[datetime] = None,
                 sensitivity_level: Optional[str] = None, entities: Optional[List[str]] = None,
                 suggested_title: Optional[str] = None, suggested_folder_id: Optional[str] = None,
                 suggested_tags: Optional[List[str]] = None, suggestions_status: str = 'pending'):
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
        self.llm_summary = llm_summary  # LLM-generated summary of the document
        self.llm_key_points = llm_key_points or []  # LLM-extracted key points list
        self.title = title  # AI-suggested title for the document
        self.document_type = document_type  # AI-classified type (e.g. 'contract', 'invoice', 'resume', 'report', 'letter')
        self.classification_confidence = classification_confidence  # confidence score 0.0-1.0 from the classifier
        self.starred = starred  # user-starred document (similar to is_favorite but explicit naming)
        self.processing_status = processing_status  # unified pipeline status: 'pending', 'extracting', 'analyzing', 'completed', 'failed'
        self.detected_language = detected_language  # ISO 639-1 language code detected in document
        self.page_count = page_count  # number of pages (for PDFs/DOCX)
        self.deadline_date = deadline_date  # AI-extracted deadline if found in document
        self.sensitivity_level = sensitivity_level  # 'public', 'internal', 'confidential', 'restricted'
        self.entities = entities or []  # AI-extracted named entities (people, companies, etc.)
        self.suggested_title = suggested_title
        self.suggested_folder_id = suggested_folder_id
        self.suggested_tags = suggested_tags or []
        self.suggestions_status = suggestions_status

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
            'is_favorite': self.is_favorite,
            'llm_summary': self.llm_summary,
            'llm_key_points': self.llm_key_points,
            'title': self.title,
            'document_type': self.document_type,
            'classification_confidence': self.classification_confidence,
            'starred': self.starred,
            'processing_status': self.processing_status,
            'detected_language': self.detected_language,
            'page_count': self.page_count,
            'deadline_date': self.deadline_date,
            'sensitivity_level': self.sensitivity_level,
            'entities': self.entities,
            'suggested_title': self.suggested_title,
            'suggested_folder_id': self.suggested_folder_id,
            'suggested_tags': self.suggested_tags,
            'suggestions_status': self.suggestions_status
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
            extraction_status=data.get('extraction_status', 'pending'),
            intelligence_status=data.get('intelligence_status', 'pending'),
            hash=data.get('hash'),
            version=data.get('version', 1),
            embedding=data.get('embedding'),
            is_favorite=data.get('is_favorite', False),
            llm_summary=data.get('llm_summary'),
            llm_key_points=data.get('llm_key_points', []),
            title=data.get('title'),
            document_type=data.get('document_type'),
            classification_confidence=data.get('classification_confidence'),
            starred=data.get('starred', False),
            processing_status=data.get('processing_status', 'pending'),
            detected_language=data.get('detected_language'),
            page_count=data.get('page_count'),
            deadline_date=data.get('deadline_date'),
            sensitivity_level=data.get('sensitivity_level'),
            entities=data.get('entities'),
            suggested_title=data.get('suggested_title'),
            suggested_folder_id=data.get('suggested_folder_id'),
            suggested_tags=data.get('suggested_tags'),
            suggestions_status=data.get('suggestions_status', 'pending')
        )
