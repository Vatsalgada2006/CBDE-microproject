#!/usr/bin/env python3
print("Testing document insights...")
try:
    from services.intelligence_service import IntelligenceService
    from services.firebase_service import firestore_db
    from models.document import Document
    
    service = IntelligenceService()
    
    # Test with a document that has extracted text
    test_doc_id = "test_doc_insights"
    test_text = "Artificial intelligence AI machine learning are transforming document processing. " \
               "These technologies enable automatic text extraction classification and sentiment analysis. " \
               "The benefits include improved efficiency reduced costs and better decision making."
    
    # Create a document in the documents collection first
    document = Document(
        doc_id=test_doc_id,
        owner_id="test_owner",
        filename="test_document.txt",
        content_type="text/plain",
        size=len(test_text),
        storage_path=f"uploads/{test_doc_id}_test_document.txt",
        extraction_status="completed",
        intelligence_status="completed"
    )
    
    # Save document to Firestore
    doc_ref = firestore_db.collection('documents').document(test_doc_id)
    doc_ref.set(document.to_dict())
    print("PASS: Test document created in Firestore")
    
    # Store the test text
    service._store_extracted_text(test_doc_id, test_text)
    print("PASS: Extracted text stored")
    
    # Test insights generation
    insights = service.get_document_insights(test_doc_id)
    print(f"PASS: Insights generated: {list(insights.keys())}")
    
    # Check that we got meaningful values
    if insights.get('word_count', 0) > 0:
        print(f"PASS: Word count: {insights['word_count']}")
    else:
        print("FAIL: Word count is zero")
        
    if insights.get('key_topics'):
        print(f"PASS: Key topics: {insights['key_topics']}")
    else:
        print("FAIL: No key topics found")
        
    # Test other insight fields
    print(f"PASS: Character count: {insights.get('character_count', 0)}")
    print(f"PASS: Summary: {insights.get('summary', 'Not found')}")
    print(f"PASS: Readability score: {insights.get('readability_score', 'Not found')}")
    print(f"PASS: Sentiment: {insights.get('sentiment', 'Not found')}")
    print(f"PASS: Language: {insights.get('language', 'Not found')}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
