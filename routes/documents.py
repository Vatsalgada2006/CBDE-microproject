import logging
from flask import Blueprint, request, jsonify, send_file, render_template, current_app
from services.firebase_service import auth
from services.document_service import DocumentService
from services.storage_service import StorageService
from services.share_service import ShareService
from models.document import Document
from models.audit_log import AuditLog
from services.audit_service import audit_service
from utils.security import sanitize_filename, validate_file_signature
import hashlib
import io
from datetime import datetime, timezone
from mimetypes import guess_type
from routes.auth import token_required

logger = logging.getLogger(__name__)

# Allowed file types for upload
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
ALLOWED_MIME_TYPES = {
    'text/plain',
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

documents_bp = Blueprint('documents', __name__)
document_service = DocumentService()
storage_service = StorageService()
share_service = ShareService()

def check_document_access(document, user_id):
    """
    Check if the user has access to the document (owner or via share).
    Returns True if access is granted and the share has not expired.
    """
    if document.owner_id == user_id:
        return True
    
    # Check if there is a share record for this document and user
    share = share_service.get_share_for_document_and_user(document.doc_id, user_id)
    if not share:
        return False
        
    # Check if share has expired
    if share_service.is_share_expired(share):
        return False
        
    # Allow access if they have a valid role or legacy permission
    if share.role in ['viewer', 'editor', 'commenter'] or share.permission in ['view', 'download']:
        return True
        
    return False

# API Routes (unchanged)
@documents_bp.route('/upload', methods=['POST'])
@token_required
def upload_document():
    """
    Upload a new document.
    Expects a multipart/form-data with a 'file' field.
    """
    logger.info("Upload endpoint called")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Sanitize the filename to prevent traversal and shell injections
    sanitized_filename_val = sanitize_filename(file.filename)

    # Check if file type is allowed by extension
    if not allowed_file(sanitized_filename_val):
        return jsonify({'error': 'File type not allowed. Please upload a valid document type.'}), 400

    # Get the current user from the request (set by token_required decorator)
    owner_id = request.user['uid']

    # Read the file data and enforce size limits
    file_data = file.read()
    file_size = len(file_data)

    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    if file_size > max_size:
        return jsonify({'error': f'File size exceeds limit of {max_size // (1024 * 1024)}MB'}), 400

    # Check file signature / magic bytes to prevent MIME spoofing
    if not validate_file_signature(file_data, sanitized_filename_val):
        return jsonify({'error': 'File content does not match its file extension (spoofing detected).'}), 400

    # Compute hash of the file for duplicate detection
    file_hash = hashlib.sha256(file_data).hexdigest()

    # Guess content type from filename
    content_type = file.content_type
    if content_type == 'application/octet-stream' or not content_type:
        content_type = guess_type(sanitized_filename_val)[0] or 'application/octet-stream'

    # Upload to Firebase Storage
    try:
        storage_url, storage_path = storage_service.upload_file(
            file_data, sanitized_filename_val, content_type=content_type
        )
        logger.info(f"Storage upload successful: {storage_path}")
    except Exception as e:
        logger.error(f"Error uploading to storage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to upload file'}), 500

    # Create document metadata
    document = Document(
        owner_id=owner_id,
        filename=sanitized_filename_val,
        content_type=content_type,
        size=file_size,
        storage_path=storage_path,
        hash=file_hash,
        extraction_status="pending",
        intelligence_status="pending"
    )
    logger.debug(f"Document metadata: {document.to_dict()}")

    # Save document metadata to Firestore
    try:
        document = document_service.create_document(document)
        logger.info(f"Document saved successfully: {document.doc_id}")

        # Log audit action
        audit_log = AuditLog(
            user_id=owner_id,
            action='DOCUMENT_UPLOAD',
            resource_type='document',
            resource_id=document.doc_id,
            details=f"Uploaded document {sanitized_filename_val} ({file_size} bytes)",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)

    except Exception as e:
        logger.error(f"Error creating document record: {e}")
        import traceback
        traceback.print_exc()
        # Delete file from storage to maintain consistency
        try:
            storage_service.delete_file(storage_path)
        except Exception as delete_err:
            logger.error(f"Failed to cleanup storage for path {storage_path}: {delete_err}")
        return jsonify({'error': 'Failed to save document metadata'}), 500

    # Process the document for intelligence (text extraction, embedding, etc.)
    # Save the uploaded file to a temporary location for text extraction
    import tempfile
    import os
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(file_data)
            tmp_file_path = tmp_file.name

        # Initialize intelligence service and process the document
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService()
        document = intelligence_service.process_document(document, tmp_file_path)

        # Clean up the temporary file
        os.unlink(tmp_file_path)
    except Exception as e:
        logger.error(f"Error during intelligence processing: {e}")
        import traceback
        traceback.print_exc()
        # We don't want to fail the upload if intelligence processing fails
        # But we should at least log it and continue

    return jsonify({
        'message': 'Document uploaded successfully',
        'document': document.to_dict()
    }), 201

@documents_bp.route('/<doc_id>', methods=['GET'])
@token_required
def get_document(doc_id):
    """
    Get document metadata by ID (API endpoint).
    """
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check if the current user has access to the document
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({'document': document.to_dict()}), 200

@documents_bp.route('/<doc_id>/download', methods=['GET'])
@token_required
def download_document(doc_id):
    """
    Download the document file.
    """
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check if the current user has access to the document
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Download the file from storage
    try:
        blob = storage_service.bucket.blob(document.storage_path)
        file_data = blob.download_as_string()
    except Exception as e:
        logger.error(f"Error downloading file from storage: {e}")
        return jsonify({'error': 'Failed to download file'}), 500

    # Log audit action
    try:
        audit_log = AuditLog(
            user_id=request.user['uid'],
            action='DOCUMENT_DOWNLOAD',
            resource_type='document',
            resource_id=doc_id,
            details=f"Downloaded document {document.filename}",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)
    except Exception as audit_err:
        logger.error(f"Failed to log download audit: {audit_err}")

    # Return the file as a downloadable response
    return send_file(
        io.BytesIO(file_data),
        mimetype=document.content_type,
        as_attachment=True,
        download_name=document.filename
    )


@documents_bp.route('/<doc_id>', methods=['PUT'])
@token_required
def update_document(doc_id):
    """
    Update document metadata.
    Expects JSON with fields to update.
    """
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Only the owner can update document metadata
    if document.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied. Only the owner can modify this document.'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update allowed fields
    allowed_fields = ['filename', 'tags', 'folder_id', 'is_favorite']
    for field in allowed_fields:
        if field in data:
            setattr(document, field, data[field])

    document.UpdatedAt = datetime.now(timezone.utc)

    try:
        document = document_service.update_document(document)
        
        # Log audit action
        audit_log = AuditLog(
            user_id=request.user['uid'],
            action='DOCUMENT_UPDATE',
            resource_type='document',
            resource_id=doc_id,
            details=f"Updated document {document.filename} fields: {list(data.keys())}",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return jsonify({'error': 'Failed to update document'}), 500

    return jsonify({
        'message': 'Document updated successfully',
        'document': document.to_dict()
    }), 200


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@token_required
def delete_document(doc_id):
    """
    Delete a document.
    """
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Only the owner can delete the document
    if document.owner_id != request.user['uid']:
        return jsonify({'error': 'Access denied. Only the owner can delete this document.'}), 403

    # Delete the file from storage
    try:
        storage_service.delete_file(document.storage_path)
    except Exception as e:
        logger.error(f"Error deleting file from storage: {e}")
        # We might still want to delete the metadata, but log the error
        pass

    # Delete the document metadata from Firestore
    try:
        document_service.delete_document(doc_id)

        # Log audit action
        audit_log = AuditLog(
            user_id=request.user['uid'],
            action='DOCUMENT_DELETE',
            resource_type='document',
            resource_id=doc_id,
            details=f"Deleted document {document.filename}",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)
    except Exception as e:
        logger.error(f"Error deleting document metadata: {e}")
        return jsonify({'error': 'Failed to delete document metadata'}), 500

    return jsonify({'message': 'Document deleted successfully'}), 200

@documents_bp.route('', methods=['GET'])
@token_required
def list_documents():
    """
    List documents for the current user (API endpoint).
    """
    owner_id = request.user['uid']

    # Get query parameters
    search_query = request.args.get('search', '')
    file_type = request.args.get('type', 'all')
    sort_by = request.args.get('sort', 'date_desc')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 12))
    folder_id = request.args.get('folder_id', None)

    # Convert folder_id to None if it's the string "null" or empty
    if folder_id in ['null', 'undefined', '']:
        folder_id = None

    # Get documents with filtering and pagination
    result = document_service.list_documents_by_owner_with_filters(
        owner_id,
        search_query=search_query,
        file_type=file_type,
        sort_by=sort_by,
        page=page,
        limit=limit,
        folder_id=folder_id
    )

    return jsonify(result), 200

@documents_bp.route('/<doc_id>/share', methods=['POST'])
@token_required
def share_document(doc_id):
    """
    Share a document with another user by email.
    Supports role-based permissions and optional expiration.
    """
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Only the owner can share a document
    if document.owner_id != request.user['uid']:
        return jsonify({'error': 'Only the document owner can share it'}), 403

    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400

    email = data['email'].strip().lower()
    role = data.get('role', 'viewer')  # viewer, editor, commenter
    permission = data.get('permission', 'view')  # legacy compat
    message = data.get('message')
    expires_at = data.get('expires_at')  # ISO 8601 string or None

    if role not in ('viewer', 'editor', 'commenter'):
        return jsonify({'error': 'Invalid role. Must be viewer, editor, or commenter'}), 400

    try:
        share = share_service.share_document(
            document_id=document.doc_id,
            owner_id=request.user['uid'],
            email=email,
            permission=permission,
            role=role,
            expires_at=expires_at,
            message=message,
        )
        return jsonify({'message': 'Document shared successfully', 'share_id': share.share_id}), 200
    except Exception as e:
        logger.error(f"Error sharing document: {e}")
        return jsonify({'error': 'Failed to share document'}), 500

# HTML Rendering Routes
@documents_bp.route('/view', methods=['GET'])
@token_required
def documents_page():
    """
    Render the documents list HTML page.
    """
    return render_template('documents.html')

@documents_bp.route('/view/<doc_id>', methods=['GET'])
@token_required
def document_view_page(doc_id):
    """
    Render the document view HTML page.
    """
    # Verify that the document exists and the user has access
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access (using the same check as in documents route)
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    return render_template('document-view.html')

@documents_bp.route('/upload/form', methods=['GET'])
@token_required
def upload_form_page():
    """
    Render the document upload form HTML page.
    """
    return render_template('upload.html')


@documents_bp.route('/deadlines/api', methods=['GET'])
@token_required
def get_deadlines_api():
    """Get all documents with upcoming deadlines."""
    try:
        user_id = request.user['uid']
        document_service = DocumentService()
        docs = document_service.list_documents_by_owner(user_id)
        
        deadline_docs = [
            doc for doc in docs 
            if getattr(doc, 'deadline_date', None) is not None
        ]
        
        # Sort by deadline (closest first)
        deadline_docs.sort(key=lambda d: d.deadline_date)
        
        return jsonify({
            'documents': [doc.to_dict() for doc in deadline_docs]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching deadlines: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/deadlines', methods=['GET'])
def deadlines_page():
    """Render the deadlines page."""
    return render_template('deadlines.html', title='Upcoming Deadlines - IntelliDoc')