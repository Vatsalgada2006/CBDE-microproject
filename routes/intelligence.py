from flask import Blueprint, request, jsonify, render_template
from services.intelligence_service import IntelligenceService
from services.document_service import DocumentService
from routes.auth import token_required

intelligence_bp = Blueprint('intelligence', __name__)
intelligence_service = IntelligenceService()
document_service = DocumentService()

@intelligence_bp.route('/<doc_id>', methods=['GET'])
@token_required
def get_intelligence(doc_id):
    """
    Get intelligence data for a document.
    """
    # Verify that the document exists and the user has access
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access (using the same check as in documents route)
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Get intelligence data
    intelligence_data = intelligence_service.get_document_intelligence(doc_id)
    return jsonify(intelligence_data), 200

@intelligence_bp.route('/<doc_id>/reprocess', methods=['POST'])
@token_required
def reprocess_intelligence(doc_id):
    """
    Re-process a document for intelligence (text extraction, embedding, etc.)
    """
    # Verify that the document exists and the user has access
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # We need the file path to re-process. Since we don't store the file locally,
    # we would need to download it from storage. For simplicity, we'll just
    # regenerate the embedding from the existing extracted text if available,
    # but we don't store the extracted text either.
    # As a workaround, we'll just update the intelligence status to pending
    # and let the next upload trigger processing? Not ideal.
    # For now, we'll return a message that reprocessing is not implemented.
    return jsonify({'error': 'Reprocessing not implemented in this version'}), 501

@intelligence_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard_page():
    """
    Render the intelligence dashboard HTML page.
    """
    return render_template('dashboard.html')

@intelligence_bp.route('/dashboard/data', methods=['GET'])
@token_required
def get_dashboard_data():
    """
    Get intelligence data for the dashboard (overview of the user's documents) as JSON.
    """
    user_id = request.user['uid']
    # Get the user's documents
    documents = document_service.list_documents_by_owner(user_id)
    total_docs = len(documents)
    total_size = sum(doc.size for doc in documents if doc.size)

    # Count documents by intelligence status
    status_counts = {
        'extraction': {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0},
        'intelligence': {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
    }
    for doc in documents:
        ext_status = doc.extraction_status if hasattr(doc, 'extraction_status') else 'unknown'
        int_status = doc.intelligence_status if hasattr(doc, 'intelligence_status') else 'unknown'
        if ext_status in status_counts['extraction']:
            status_counts['extraction'][ext_status] += 1
        else:
            status_counts['extraction']['unknown'] = status_counts['extraction'].get('unknown', 0) + 1
        if int_status in status_counts['intelligence']:
            status_counts['intelligence'][int_status] += 1
        else:
            status_counts['intelligence']['unknown'] = status_counts['intelligence'].get('unknown', 0) + 1

    # Get recent documents (latest 5)
    recent_docs = sorted(documents, key=lambda d: d.CreatedAt if d.CreatedAt else datetime.min, reverse=True)[:5]
    recent_docs_data = [doc.to_dict() for doc in recent_docs]

    # Count duplicates and versions (we would need to query the relationships collection)
    # For simplicity, we'll skip this for now and just return zeros.
    duplicate_count = 0
    version_count = 0
    relationship_count = 0

    dashboard_data = {
        'total_documents': total_docs,
        'total_size_bytes': total_size,
        'extraction_status_counts': status_counts['extraction'],
        'intelligence_status_counts': status_counts['intelligence'],
        'recent_documents': recent_docs_data,
        'duplicate_count': duplicate_count,
        'version_count': version_count,
        'relationship_count': relationship_count
    }

    return jsonify(dashboard_data), 200