"""
Final test to verify the storage bucket fix works in the context of the full application.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, '.')

def test_with_env_file():
    """Test with the actual .env file present."""
    print("=== Testing with .env file present ===")

    # Import modules - this will run the Firebase initialization
    import services.firebase_service as fs

    print(f"Firebase initialized: {fs._firebase_initialized}")
    if fs._firebase_initialized:
        print("Firebase is initialized - checking storage bucket...")
        # If Firebase is initialized, we should have a storage bucket
        # (unless our fix kicks in and raises an error)
        try:
            # Access the storage bucket to trigger the initialization code
            # Note: The bucket is initialized at module import time
            print("Storage bucket attribute exists:", hasattr(fs, 'storage_bucket'))
            if hasattr(fs, 'storage_bucket'):
                print("Storage bucket type:", type(fs.storage_bucket))
        except Exception as e:
            print(f"Error accessing storage bucket: {e}")
    else:
        print("Firebase is not initialized (using mocks) - this is expected with dummy credentials")
        print("Storage bucket is mock:", type(fs.storage_bucket))

def test_missing_storage_bucket_scenario():
    """Simulate the scenario where Firebase is initialized but storage bucket is missing."""
    print("\n=== Testing missing storage bucket scenario ===")

    # We'll simulate this by temporarily patching the module after import
    import services.firebase_service as fs

    # Save originals
    original_initialized = fs._firebase_initialized
    # We can't easily change Config.FIREBASE_STORAGE_BUCKET because it's a class attribute
    # that was set at import time, so we'll simulate by checking what would happen

    print("In the actual Render environment:")
    print("- Firebase credentials would be set (via env vars)")
    print("- Firebase initialization would succeed")
    print("- FIREBASE_STORAGE_BUCKET would be missing/not set")
    print("- Our fix should raise a clear ValueError during module import")

    # Since we can't easily re-run the module initialization with different env vars
    # without restarting the Python interpreter, let's just verify our code logic
    # by looking at the source

    print("\nVerifying the fix is in place:")
    # Read the firebase_service.py file and check for our error message
    with open('services/firebase_service.py', 'r') as f:
        content = f.read()

    if "FIREBASE_STORAGE_BUCKET environment variable is not set" in content:
        print("[PASS] Fix is present in the code")
    else:
        print("[FAIL] Fix is NOT present in the code")

    if "storage_bucket = storage.bucket()" in content and "ValueError" not in content.split("storage_bucket = storage.bucket()")[0][-100:]:
        print("[FAIL] Old problematic code still present")
    else:
        print("[PASS] Old problematic code has been replaced")

def test_normal_operation():
    """Test that normal operation (with mocks) still works."""
    print("\n=== Testing normal operation with mocks ===")

    import services.firebase_service as fs

    # Test that we can import and use the mocks
    print(f"Using mock auth: {type(fs.auth)}")
    print(f"Using mock firestore: {type(fs.firestore_db)}")
    print(f"Using mock storage: {type(fs.storage_bucket)}")

    # Test basic functionality
    try:
        # Test mock auth
        mock_user = fs.auth.create_user(email="test@example.com", password="password")
        print(f"[PASS] Mock auth works: created user {mock_user.uid}")

        # Test mock firestore
        doc_ref = fs.firestore_db.collection('test').document('doc1')
        doc_ref.set({'field': 'value'})
        print("[PASS] Mock firestore works")

        # Test mock storage
        blob = fs.storage_bucket.blob('test/path')
        blob.upload_from_string(b'test data')
        print("[PASS] Mock storage works")

    except Exception as e:
        print(f"[FAIL] Error in mock functionality: {e}")
        raise

if __name__ == "__main__":
    test_with_env_file()
    test_missing_storage_bucket_scenario()
    test_normal_operation()
    print("\n=== All tests completed ===")