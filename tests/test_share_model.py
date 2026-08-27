"""
Comprehensive tests for the Share model.
"""
import sys
import os
from datetime import datetime, timezone

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('.'))

from models.share import Share


def test_share_creation_defaults():
    """Test creating a share with default values."""
    share = Share(
        share_id="share1",
        document_id="doc1",
        owner_id="user1"
    )

    assert share.share_id == "share1"
    assert share.document_id == "doc1"
    assert share.owner_id == "user1"
    assert share.shared_with_id is None
    assert share.permission is None
    assert share.CreatedAt is not None
    assert share.shared_with_email is None
    assert share.role == 'viewer'
    assert share.expires_at is None
    assert share.is_link_share is False
    assert share.share_link_token is None
    assert share.message is None
    assert share.accepted is False


def test_share_creation_all_fields():
    """Test creating a share with all fields explicitly set."""
    created_at = datetime.now(timezone.utc)
    expires_at = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    share = Share(
        share_id="share123",
        document_id="doc123",
        owner_id="user123",
        shared_with_id="user456",
        permission="view",
        CreatedAt=created_at,
        shared_with_email="colleague@example.com",
        role="editor",
        expires_at=expires_at,
        is_link_share=True,
        share_link_token="token_abc_123",
        message="Please review this doc",
        accepted=True
    )

    assert share.share_id == "share123"
    assert share.document_id == "doc123"
    assert share.owner_id == "user123"
    assert share.shared_with_id == "user456"
    assert share.permission == "view"
    assert share.CreatedAt == created_at
    assert share.shared_with_email == "colleague@example.com"
    assert share.role == "editor"
    assert share.expires_at == expires_at
    assert share.is_link_share is True
    assert share.share_link_token == "token_abc_123"
    assert share.message == "Please review this doc"
    assert share.accepted is True


def test_share_to_dict_and_from_dict():
    """Test round-trip conversion between Share instance and dict."""
    created_at = datetime.now(timezone.utc)
    expires_at = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    original_share = Share(
        share_id="share123",
        document_id="doc123",
        owner_id="user123",
        shared_with_id="user456",
        permission="view",
        CreatedAt=created_at,
        shared_with_email="colleague@example.com",
        role="commenter",
        expires_at=expires_at,
        is_link_share=True,
        share_link_token="token_xyz",
        message="Let me know your thoughts",
        accepted=True
    )

    data = original_share.to_dict()

    assert data['share_id'] == "share123"
    assert data['document_id'] == "doc123"
    assert data['owner_id'] == "user123"
    assert data['shared_with_id'] == "user456"
    assert data['permission'] == "view"
    assert data['CreatedAt'] == created_at
    assert data['shared_with_email'] == "colleague@example.com"
    assert data['role'] == "commenter"
    assert data['expires_at'] == expires_at
    assert data['is_link_share'] is True
    assert data['share_link_token'] == "token_xyz"
    assert data['message'] == "Let me know your thoughts"
    assert data['accepted'] is True

    restored_share = Share.from_dict(data)

    assert restored_share.share_id == original_share.share_id
    assert restored_share.document_id == original_share.document_id
    assert restored_share.owner_id == original_share.owner_id
    assert restored_share.shared_with_id == original_share.shared_with_id
    assert restored_share.permission == original_share.permission
    assert restored_share.CreatedAt == original_share.CreatedAt
    assert restored_share.shared_with_email == original_share.shared_with_email
    assert restored_share.role == original_share.role
    assert restored_share.expires_at == original_share.expires_at
    assert restored_share.is_link_share == original_share.is_link_share
    assert restored_share.share_link_token == original_share.share_link_token
    assert restored_share.message == original_share.message
    assert restored_share.accepted == original_share.accepted


def test_share_from_dict_defaults():
    """Test from_dict with minimal data using defaults."""
    data = {
        'share_id': 's1',
        'document_id': 'd1'
    }

    share = Share.from_dict(data)
    assert share.share_id == 's1'
    assert share.document_id == 'd1'
    assert share.owner_id is None
    assert share.shared_with_id is None
    assert share.permission is None
    assert share.shared_with_email is None
    assert share.role == 'viewer'
    assert share.expires_at is None
    assert share.is_link_share is False
    assert share.share_link_token is None
    assert share.message is None
    assert share.accepted is False
