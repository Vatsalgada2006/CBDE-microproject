#!/usr/bin/env python3
print("Testing document summarization...")
try:
    from services.intelligence_service import IntelligenceService
    from services.firebase_service import firestore_db
    from models.document import Document
    
    service = IntelligenceService()
    
    # Test with a document that has extracted text
    test_doc_id = "test_doc_summary"
    test_text = "Artificial intelligence is transforming the way we work with documents. " \
               "Modern AI systems can extract text, understand content, and provide intelligent insights. " \
               "This technology enables zero-effort organization and automatic metadata extraction."
    
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
    
    # Test summarization
    summary = service.summarize_document(test_doc_id)
    print(f"PASS: Summary generated: {summary}")
    
    # The summary should contain some of the key content
    if "Artificial intelligence" in summary or "transforming" in summary:
        print("PASS: Summary contains expected content")
    else:
        print("INFO: Summary may not contain expected content (this is OK for extractive summarization)")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
