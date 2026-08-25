"""
Comprehensive tests for the Document model.
"""
import sys
import os
from datetime import datetime, timezone

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('.'))

from models.document import Document


def test_document_creation():
    """Test that a document can be created with basic attributes."""
    doc = Document(
        filename="test.pdf",
        content_type="application/pdf",
        size=1024,
        owner_id="user123"
    )

    assert doc.filename == "test.pdf"
    assert doc.content_type == "application/pdf"
    assert doc.size == 1024
    assert doc.owner_id == "user123"
    assert doc.extraction_status == "pending"
    assert doc.intelligence_status == "pending"
    assert doc.version == 1
    assert doc.is_favorite == False
    assert doc.tags == []
    assert doc.hash is None
    assert doc.storage_path is None
    assert doc.folder_id is None
    assert doc.CreatedAt is not None
    assert doc.UpdatedAt is not None


def test_document_to_from_dict():
    """Test that a document can be converted to dict and back."""
    # Create a document with all fields
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc)
    
    original_doc = Document(
        doc_id="doc123",
        owner_id="user123",
        filename="test.pdf",
        content_type="application/pdf",
        size=1024,
        storage_path="uploads/test.pdf",
        hash="abc123def456",
        version=2,
        extraction_status="completed",
        intelligence_status="completed",
        is_favorite=True,
        tags=["important", "contract"],
        folder_id="folder456",
        CreatedAt=created_at,
        UpdatedAt=updated_at
    )

    # Convert to dict
    doc_dict = original_doc.to_dict()

    # Verify dict contents
    assert doc_dict['filename'] == "test.pdf"
    assert doc_dict['content_type'] == "application/pdf"
    assert doc_dict['size'] == 1024
    assert doc_dict['owner_id'] == "user123"
    assert doc_dict['hash'] == "abc123def456"
    assert doc_dict['extraction_status'] == "completed"
    assert doc_dict['intelligence_status'] == "completed"
    assert doc_dict['is_favorite'] == True
    assert doc_dict['tags'] == ["important", "contract"]
    assert doc_dict['folder_id'] == "folder456"
    assert doc_dict['version'] == 2
    assert doc_dict['CreatedAt'] == created_at
    assert doc_dict['UpdatedAt'] == updated_at

    # Create from dict
    restored_doc = Document.from_dict(doc_dict)

    # Verify round-trip
    assert restored_doc.filename == original_doc.filename
    assert restored_doc.content_type == original_doc.content_type
    assert restored_doc.size == original_doc.size
    assert restored_doc.owner_id == original_doc.owner_id
    assert restored_doc.hash == original_doc.hash
    assert restored_doc.extraction_status == original_doc.extraction_status
    assert restored_doc.intelligence_status == original_doc.intelligence_status
    assert restored_doc.is_favorite == original_doc.is_favorite
    assert restored_doc.tags == original_doc.tags
    assert restored_doc.folder_id == original_doc.folder_id
    assert restored_doc.version == original_doc.version
    assert restored_doc.CreatedAt == original_doc.CreatedAt
    assert restored_doc.UpdatedAt == original_doc.UpdatedAt
    assert restored_doc.doc_id == original_doc.doc_id


def test_document_default_values():
    """Test that document has correct default values."""
    doc = Document(
        filename="test.txt",
        content_type="text/plain",
        size=512,
        owner_id="user456"
    )

    assert doc.version == 1
    assert doc.is_favorite == False
    assert doc.tags == []
    assert doc.extraction_status == "pending"
    assert doc.intelligence_status == "pending"
    assert doc.CreatedAt is not None
    assert doc.UpdatedAt is not None
    assert doc.storage_path is None
    assert doc.hash is None
    assert doc.folder_id is None


def test_document_from_dict_missing_fields():
    """Test creating document from dict with missing fields (should use defaults)."""
    partial_data = {
        'filename': 'test.docx',
        'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'size': 2048,
        'owner_id': 'user789'
    }
    
    doc = Document.from_dict(partial_data)
    
    assert doc.filename == "test.docx"
    assert doc.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert doc.size == 2048
    assert doc.owner_id == "user789"
    assert doc.version == 1  # default
    assert doc.is_favorite == False  # default
    assert doc.tags == []  # default
    assert doc.extraction_status == "pending"  # default
    assert doc.intelligence_status == "pending"  # default
    assert doc.doc_id is None  # not provided
    assert doc.storage_path is None  # not provided
    assert doc.hash is None  # not provided
    assert doc.folder_id is None  # not provided
    assert doc.CreatedAt is not None  # should be set
    assert doc.UpdatedAt is not None  # should be set


if __name__ == "__main__":
    test_document_creation()
    test_document_to_from_dict()
    test_document_default_values()
    test_document_from_dict_missing_fields()
    print("All tests passed!")
