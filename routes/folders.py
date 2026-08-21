from flask import Blueprint, request, jsonify
from services.folder_service import FolderService
from services.document_service import DocumentService
from models.folder import Folder
from routes.auth import token_required

folders_bp = Blueprint('folders', __name__)
folder_service = FolderService()
document_service = DocumentService()

@folders_bp.route('', methods=['POST'])
@token_required
def create_folder():
    """
    Create a new folder.
    Expects JSON: { "name": "Folder Name", "parent_id": "Optional Parent Folder ID" }
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Folder name is required'}), 400

    name = data['name']
    parent_id = data.get('parent_id')

    # Get the current user from the request (set by token_required decorator)
    owner_id = request.user['uid']

    folder = Folder(
        owner_id=owner_id,
        name=name,
        parent_id=parent_id
    )

    try:
        folder = folder_service.create_folder(folder)
        return jsonify({
            'message': 'Folder created successfully',
            'folder': folder.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create folder: {str(e)}'}), 500

@folders_bp.route('/<folder_id>', methods=['GET'])
@token_required
def get_folder(folder_id):
    """
    Get folder details by ID.
    """
    folder = folder_service.get_folder(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    # Check if the current user is the owner
    if folder.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({'folder': folder.to_dict()}), 200

@folders_bp.route('/<folder_id>', methods=['PUT'])
@token_required
def update_folder(folder_id):
    """
    Update folder metadata.
    Expects JSON with fields to update.
    """
    folder = folder_service.get_folder(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    # Check if the current user is the owner
    if folder.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update allowed fields
    allowed_fields = ['name', 'parent_id']
    for field in allowed_fields:
        if field in data:
            setattr(folder, field, data[field])

    try:
        folder = folder_service.update_folder(folder)
        return jsonify({
            'message': 'Folder updated successfully',
            'folder': folder.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update folder: {str(e)}'}), 500

@folders_bp.route('/<folder_id>', methods=['DELETE'])
@token_required
def delete_folder(folder_id):
    """
    Delete a folder.
    """
    folder = folder_service.get_folder(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    # Check if the current user is the owner
    if folder.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied'}), 403

    # TODO: Check if folder is empty before deleting (optional)
    try:
        folder_service.delete_folder(folder_id)
        return jsonify({'message': 'Folder deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete folder: {str(e)}'}), 500

@folders_bp.route('', methods=['GET'])
@token_required
def list_folders():
    """
    List folders for the current user.
    """
    owner_id = request.user['uid']
    folders = folder_service.list_folders_by_owner(owner_id)
    return jsonify({
        'folders': [folder.to_dict() for folder in folders]
    }), 200

@folders_bp.route('/<folder_id>/documents', methods=['GET'])
@token_required
def list_documents_in_folder(folder_id):
    """
    List documents in a specific folder.
    """
    folder = folder_service.get_folder(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    # Check if the current user is the owner
    if folder.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied'}), 403

    documents = document_service.list_documents_by_folder(folder_id)
    return jsonify({
        'documents': [doc.to_dict() for doc in documents]
    }), 200