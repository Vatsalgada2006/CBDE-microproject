import logging
from flask import Blueprint, request, jsonify, render_template
from routes.auth import token_required
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint('intelligence', __name__)

# Lazy initialization of services to avoid loading heavy models at startup
def get_intelligence_service():
    from services.intelligence_service import IntelligenceService
    return IntelligenceService()

def get_document_service():
    from services.document_service import DocumentService
    return DocumentService()

@intelligence_bp.route('/<doc_id>', methods=['GET'])
@token_required
def get_intelligence(doc_id):
    """
    Get intelligence data for a document.
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access (using the same check as in documents route)
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Get intelligence data
    intelligence_service = get_intelligence_service()
    intelligence_data = intelligence_service.get_document_intelligence(doc_id)
    return jsonify(intelligence_data), 200

@intelligence_bp.route('/document/<doc_id>/data', methods=['GET'])
@token_required
def get_document_intelligence_data(doc_id):
    """
    Get formatted intelligence data for document view page.
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Get intelligence data
    intelligence_service = get_intelligence_service()
    intelligence_data = intelligence_service.get_document_intelligence(doc_id)

    # Format the data for the document view page
    formatted_data = {
        'actions': intelligence_data.get('actions', []),
        'relationships': intelligence_data.get('relationships', []),
        'classification': intelligence_data.get('classification', {}),
        'versions': []  # We'll extract versions from relationships if needed
    }

    # Extract version-like relationships
    relationships = intelligence_data.get('relationships', [])
    version_relationships = [rel for rel in relationships if rel.get('relationship_type', '').startswith('version')]
    formatted_data['versions'] = version_relationships

    return jsonify(formatted_data), 200

@intelligence_bp.route('/<doc_id>/reprocess', methods=['POST'])
@token_required
def reprocess_intelligence(doc_id):
    """
    Re-process a document for intelligence (text extraction, embedding, etc.)
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
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
    document_service = get_document_service()
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

    # Get folder count
    folder_service = None
    try:
        from services.folder_service import FolderService
        folder_service = FolderService()
        folders = folder_service.list_folders_by_owner(user_id)
        total_folders = len(folders)
    except Exception as e:
        logger.error(f"Error getting folder count: {e}")
        total_folders = 0

    # Get shared documents count (documents shared with the user)
    share_service = None
    try:
        from services.share_service import ShareService
        share_service = ShareService()
        shares = share_service.list_shares_shared_with(user_id)
        total_shared = len(shares)
    except Exception as e:
        logger.error(f"Error getting shared count: {e}")
        total_shared = 0

    # Count documents that have been processed by AI (intelligence status completed)
    ai_processed = len([doc for doc in documents if hasattr(doc, 'intelligence_status') and doc.intelligence_status == 'completed'])

    # Count duplicates and versions (we would need to query the relationships collection)
    # For simplicity, we'll skip this for now and just return zeros.
    duplicate_count = 0
    version_count = 0
    relationship_count = 0

    dashboard_data = {
        'total_documents': total_docs,
        'total_folders': total_folders,
        'total_shared': total_shared,
        'ai_processed': ai_processed,
        'total_size_bytes': total_size,
        'extraction_status_counts': status_counts['extraction'],
        'intelligence_status_counts': status_counts['intelligence'],
        'recent_documents': recent_docs_data,
        'duplicate_count': duplicate_count,
        'version_count': version_count,
        'relationship_count': relationship_count
    }

    return jsonify(dashboard_data), 200

@intelligence_bp.route('/summarize/<doc_id>', methods=['GET'])
@token_required
def summarize_document(doc_id):
    """
    Generate a summary of a document.
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Generate summary
    intelligence_service = get_intelligence_service()
    summary = intelligence_service.summarize_document(doc_id)

    return jsonify({'summary': summary}), 200

@intelligence_bp.route('/search', methods=['POST'])
@token_required
def semantic_search():
    """
    Perform semantic search on documents.
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    query = data['query']
    user_id = request.user['uid']

    # Perform semantic search
    intelligence_service = get_intelligence_service()
    results = intelligence_service.semantic_search(query, user_id)

    # Format results
    formatted_results = []
    for result in results:
        doc = result['document']
        formatted_results.append({
            'doc_id': doc.doc_id,
            'filename': doc.filename,
            'similarity': result['similarity'],
            'content_type': doc.content_type,
            'size': doc.size,
            'CreatedAt': doc.CreatedAt
        })

    return jsonify({'results': formatted_results}), 200

@intelligence_bp.route('/insights/<doc_id>', methods=['GET'])
@token_required
def get_document_insights(doc_id):
    """
    Get insights for a document.
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Get insights
    intelligence_service = get_intelligence_service()
    insights = intelligence_service.get_document_insights(doc_id)

    return jsonify(insights)


@intelligence_bp.route('/ask/<doc_id>', methods=['POST'])
@token_required
def ask_document_question(doc_id):
    """
    Ask a question about a document.
    Expects JSON: { "question": "your question here" }
    """
    # Verify that the document exists and the user has access
    document_service = get_document_service()
    document = document_service.get_document(doc_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Check access
    from routes.documents import check_document_access
    if not check_document_access(document, request.user['uid']):
        return jsonify({'error': 'Access denied'}), 403

    # Get the question from the request
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'Question is required'}), 400

    question = data['question']
    if not question or not question.strip():
        return jsonify({'error': 'Question cannot be empty'}), 400

    # Get answer from intelligence service
    intelligence_service = get_intelligence_service()
    result = intelligence_service.ask_document_question(doc_id, question.strip())

    return jsonify(result), 200