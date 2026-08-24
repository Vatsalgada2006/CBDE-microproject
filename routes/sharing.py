from flask import Blueprint, request, jsonify
from services.share_service import ShareService
from services.document_service import DocumentService
from models.share import Share
from routes.auth import token_required

sharing_bp = Blueprint('sharing', __name__)
share_service = ShareService()
document_service = DocumentService()

@sharing_bp.route('', methods=['POST'])
@token_required
def create_share():
    """
    Share a document with another user.
    Expects JSON: { "document_id": "Document ID", "shared_with_email": "Email of the user to share with", "permission": "view or download" }
    Note: In a real system, we would look up the user ID by email. For simplicity, we'll assume the shared_with_email is the user ID (UID).
    """
    data = request.get_json()
    if not data or 'document_id' not in data or 'shared_with_email' not in data:
        return jsonify({'error': 'Document ID and shared_with_email are required'}), 400

    document_id = data['document_id']
    shared_with_id = data['shared_with_email']  # In a real app, we would map email to UID

    # Validate user ID is not empty
    if not shared_with_id or not shared_with_id.strip():
        return jsonify({'error': 'User ID is required'}), 400

    permission = data.get('permission', 'view')

    # Validate permission
    if permission not in ['view', 'download']:
        return jsonify({'error': "Permission must be either 'view' or 'download'"}), 400

    # Get the current user from the request (set by token_required decorator)
    owner_id = request.user['uid']

    # Verify that the current user owns the document
    document = document_service.get_document(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    if document.owner_id != owner_id:
        return jsonify({'error': 'Only the owner can share the document'}), 403

    # TODO: In a real system, we would check if the shared_with_id corresponds to a valid user
    # For now, we'll proceed

    share = Share(
        document_id=document_id,
        owner_id=owner_id,
        shared_with_id=shared_with_id,
        permission=permission
    )

    try:
        share = share_service.create_share(share)
        return jsonify({
            'message': 'Document shared successfully',
            'share': share.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': f'Failed to share document: {str(e)}'}), 500

@sharing_bp.route('/<share_id>', methods=['GET'])
@token_required
def get_share(share_id):
    """
    Get share details by ID.
    """
    share = share_service.get_share(share_id)
    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Check if the current user is either the owner or the shared-with user
    if share.owner_id != request.user['uid'] and share.shared_with_id != request.user['uid']:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({'share': share.to_dict()}), 200

@sharing_bp.route('/<share_id>', methods=['PUT'])
@token_required
def update_share(share_id):
    """
    Update share metadata.
    Expects JSON with fields to update.
    """
    share = share_service.get_share(share_id)
    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Check if the current user is the owner (only owner can update share)
    if share.owner_id != request.user['uid']:
        return jsonify({'error': 'Only the owner can update the share'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update allowed fields
    allowed_fields = ['permission']
    for field in allowed_fields:
        if field in data:
            setattr(share, field, data[field])

    try:
        share = share_service.update_share(share)
        return jsonify({
            'message': 'Share updated successfully',
            'share': share.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update share: {str(e)}'}), 500

@sharing_bp.route('/<share_id>', methods=['DELETE'])
@token_required
def delete_share(share_id):
    """
    Delete a share.
    """
    share = share_service.get_share(share_id)
    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Check if the current user is the owner (only owner can delete share)
    if share.owner_id != request.user['uid']:
        return jsonify({'error': 'Only the owner can delete the share'}), 403

    try:
        share_service.delete_share(share_id)
        return jsonify({'message': 'Share deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete share: {str(e)}'}), 500

@sharing_bp.route('', methods=['GET'])
@token_required
def list_shares():
    """
    List shares for the current user (both as owner and as shared-with).
    """
    owner_id = request.user['uid']
    # Get shares where the user is the owner
    shares_as_owner = share_service.list_shares_by_owner(owner_id)
    # Get shares where the user is the shared-with user
    shares_as_shared_with = share_service.list_shares_shared_with(owner_id)
    # Combine and remove duplicates (by share_id)
    all_shares = {share.share_id: share for share in shares_as_owner + shares_as_shared_with}
    return jsonify({
        'shares': [share.to_dict() for share in all_shares.values()]
    }), 200

@sharing_bp.route('/document/<document_id>', methods=['GET'])
@token_required
def get_shares_for_document(document_id):
    """
    List all shares for a specific document.
    """
    # Verify that the current user owns the document
    document = document_service.get_document(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    if document.owner_id != request.user['uid']:
        return jsonify({'error': 'Only the owner can view shares for the document'}), 403

    # Get shares where the document is being shared
    try:
        query = share_service.db.collection('shares').where('document_id', '==', document_id)
        shares = []
        for share in query.stream():
            shares.append(Share.from_dict(share.to_dict()).to_dict())
        return jsonify({
            'shares': shares
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get shares for document: {str(e)}'}), 500