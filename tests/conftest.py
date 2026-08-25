"""
Pytest configuration and fixtures for IntelliDoc application.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('.'))


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    from app import create_app
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def mock_firebase():
    """Mock Firebase services."""
    with patch('services.firebase_service.auth') as mock_auth, \
         patch('services.firebase_service.firestore_db') as mock_firestore, \
         patch('services.firebase_service.storage_bucket') as mock_storage:
        yield {
            'auth': mock_auth,
            'firestore': mock_firestore,
            'storage': mock_storage
        }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'uid': 'test_uid_123',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'photo_url': 'https://example.com/photo.jpg'
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    from datetime import datetime, timezone
    return {
        'doc_id': 'test_doc_id_123',
        'owner_id': 'test_uid_123',
        'filename': 'test_document.pdf',
        'content_type': 'application/pdf',
        'size': 1024000,
        'storage_path': 'uploads/test_document.pdf',
        'CreatedAt': datetime.now(timezone.utc),
        'UpdatedAt': datetime.now(timezone.utc),
        'hash': 'a' * 64,
        'version': 1,
        'extraction_status': 'completed',
        'intelligence_status': 'completed',
        'is_favorite': False
    }
