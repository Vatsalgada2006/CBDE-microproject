#!/usr/bin/env python3
print("Testing extracted text storage...")
try:
    from services.intelligence_service import IntelligenceService
    from services.firebase_service import firestore_db
    from models.document import Document
    
    service = IntelligenceService()
    
    # Test document ID
    test_doc_id = "test_doc_123"
    test_text = "This is a test document for verifying extracted text storage and retrieval functionality."
    
    # Store extracted text
    service._store_extracted_text(test_doc_id, test_text)
    print("PASS: Extracted text stored successfully")
    
    # Retrieve extracted text
    retrieved_text = service._get_extracted_text(test_doc_id)
    if retrieved_text == test_text:
        print("PASS: Extracted text retrieved successfully and matches original")
    else:
        print("FAIL: Extracted text retrieval failed or mismatch")
        print(f"  Expected: {test_text}")
        print(f"  Got: {retrieved_text}")
        
    # Test retrieving non-existent document
    non_existent_text = service._get_extracted_text("non_existent_doc")
    if non_existent_text is None:
        print("PASS: Non-existent document correctly returns None")
    else:
        print("FAIL: Non-existent document should return None")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
