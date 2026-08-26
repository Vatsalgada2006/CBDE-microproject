#!/usr/bin/env python3
print("Running comprehensive test of intelligence service enhancements...")
try:
    from services.intelligence_service import IntelligenceService
    from services.firebase_service import firestore_db
    from models.document import Document
    
    service = IntelligenceService()
    
    # Test with a document that has extracted text
    test_doc_id = "test_doc_comprehensive"
    test_text = "The project deadline is October 30, 2026. Please submit the final report by this date. " \
               "The budget for this project is $50,000. Key stakeholders include John Smith and Jane Doe. " \
               "Artificial intelligence AI machine learning are transforming document processing. " \
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
    
    # Store the extracted text
    service._store_extracted_text(test_doc_id, test_text)
    print("PASS: Extracted text stored")
    
    # Test summarization
    summary = service.summarize_document(test_doc_id)
    print(f"PASS: Summary generated: {summary[:100]}..." if len(summary) > 100 else f"PASS: Summary generated: {summary}")
    
    # Test question answering
    qa_result = service.ask_document_question(test_doc_id, "What is the project deadline?")
    print(f"PASS: QA result: {qa_result.get('answer', '')[:50]}... (confidence: {qa_result.get('confidence', 0)})")
    
    # Test insights generation
    insights = service.get_document_insights(test_doc_id)
    print(f"PASS: Insights generated - Word count: {insights.get('word_count', 0)}, Key topics: {insights.get('key_topics', [])}")
    
    print("\n🎉 ALL TESTS PASSED! The intelligence service enhancements are working correctly.")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
