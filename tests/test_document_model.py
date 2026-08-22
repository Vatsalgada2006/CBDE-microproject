"""
Basic test for the Document model to verify the testing structure works.
"""
import sys
import os
from datetime import datetime

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
    print("[PASS] Document creation test passed")

def test_document_to_from_dict():
    """Test that a document can be converted to dict and back."""
    # Create a document
    original_doc = Document(
        filename="test.pdf",
        content_type="application/pdf",
        size=1024,
        owner_id="user123",
        hash="abc123",
        extraction_status="completed",
        intelligence_status="completed"
    )
    original_doc.doc_id = "doc123"
    original_doc.CreatedAt = datetime.utcnow()
    original_doc.UpdatedAt = datetime.utcnow()

    # Convert to dict
    doc_dict = original_doc.to_dict()

    # Verify dict contents
    assert doc_dict['filename'] == "test.pdf"
    assert doc_dict['content_type'] == "application/pdf"
    assert doc_dict['size'] == 1024
    assert doc_dict['owner_id'] == "user123"
    assert doc_dict['hash'] == "abc123"
    assert doc_dict['extraction_status'] == "completed"
    assert doc_dict['intelligence_status'] == "completed"
    assert doc_dict['doc_id'] == "doc123"

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
    assert restored_doc.doc_id == original_doc.doc_id
    print("[PASS] Document to/from dict test passed")

if __name__ == "__main__":
    test_document_creation()
    test_document_to_from_dict()
    print("All tests passed!")