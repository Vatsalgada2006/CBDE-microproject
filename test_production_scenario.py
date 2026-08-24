"""
Test the production scenario: Firebase initialized successfully but
FIREBASE_STORAGE_BUCKET is missing/not set.
This simulates what would happen in Render with valid Firebase credentials
but missing storage bucket configuration.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, '.')

def test_production_scenario():
    """Test: Firebase works but storage bucket missing -> should raise clear error"""

    # Clear any existing Firebase-related env vars
    for key in list(os.environ.keys()):
        if key.startswith('FIREBASE_') or key == 'FLASK_SECRET_KEY':
            del os.environ[key]

    # Set up Firebase config that would allow initialization to succeed
    # (We'll use valid format but prevent actual network calls by mocking)
    os.environ['FIREBASE_PROJECT_ID'] = 'test-project-123'
    os.environ['FIREBASE_CLIENT_EMAIL'] = 'test@test-project-123.iam.gserviceaccount.com'
    # Note: Intentionally NOT setting FIREBASE_STORAGE_BUCKET to simulate the issue

    # Use a dummy private key in correct format
    os.environ['FIREBASE_PRIVATE_KEY'] = '''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDfakekey123
-----END PRIVATE KEY-----'''

    print("Environment variables set:")
    print(f"  FIREBASE_PROJECT_ID: {os.environ.get('FIREBASE_PROJECT_ID')}")
    print(f"  FIREBASE_CLIENT_EMAIL: {os.environ.get('FIREBASE_CLIENT_EMAIL')}")
    print(f"  FIREBASE_STORAGE_BUCKET: {os.environ.get('FIREBASE_STORAGE_BUCKET', 'NOT SET')}")

    # Now we need to prevent the actual Firebase initialization from making network calls
    # We'll patch the initialize_firebase function to simulate success
    import services.firebase_service as fs

    # Save original function
    original_initialize_firebase = fs.initialize_firebase

    # Mock initialize_firebase to simulate success
    def mock_initialize_firebase_success():
        fs._firebase_initialized = True
        # Create a mock firebase app object
        class MockFirebaseApp:
            pass
        fs.firebase_app = MockFirebaseApp()
        print("Mock: Firebase initialization succeeded")

    # Apply the patch
    fs.initialize_firebase = mock_initialize_firebase_success

    try:
        # Force re-initialization by clearing the flag and calling init
        fs._firebase_initialized = False
        fs.firebase_app = None

        # Now import/reload the module to trigger our fixed code
        # We need to be careful about module state
        import importlib
        importlib.reload(fs)

        print("\nAfter module reload:")
        print(f"  _firebase_initialized: {fs._firebase_initialized}")

        if fs._firebase_initialized:
            print("Firebase is initialized (as expected from our mock)")
            # Now check if our fix works properly
            from config import Config

            # Verify that FIREBASE_STORAGE_BUCKET is indeed missing/not set
            bucket_config = getattr(Config, 'FIREBASE_STORAGE_BUCKET', None)
            print(f"  Config.FIREBASE_STORAGE_BUCKET: {bucket_config}")

            if not bucket_config:
                print("As expected, storage bucket is not configured")
                print("Testing that our fix raises the appropriate error...")

                # The storage_bucket variable should have been set during module import
                # Let's check what happened
                if hasattr(fs, 'storage_bucket'):
                    print("ERROR: storage_bucket attribute exists - this means our fix didn't work!")
                    print(f"  storage_bucket type: {type(fs.storage_bucket)}")
                    return False
                else:
                    print("GOOD: storage_bucket attribute does not exist (as expected if init failed)")
                    # But we need to check if the module import actually failed due to our ValueError

        else:
            print("Firebase is not initialized - this would happen if our mock didn't work")
            return False

    except ValueError as e:
        # This is what we EXPECT to happen - our fix should raise a clear ValueError
        error_msg = str(e)
        print(f"SUCCESS: Caught expected ValueError: {error_msg}")

        # Verify it's the right error message
        if "FIREBASE_STORAGE_BUCKET environment variable is not set" in error_msg:
            print("SUCCESS: Error message is clear and actionable")
            return True
        else:
            print(f"ERROR: Error message doesn't contain expected text: {error_msg}")
            return False

    except Exception as e:
        print(f"ERROR: Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore original function
        fs.initialize_firebase = original_initialize_firebase
        # Clean up environment variables
        for key in list(os.environ.keys()):
            if key.startswith('FIREBASE_') or key == 'FLASK_SECRET_KEY':
                del os.environ[key]

if __name__ == "__main__":
    print("Testing production scenario: Firebase initialized but storage bucket missing")
    print("=" * 80)

    success = test_production_scenario()

    print("\n" + "=" * 80)
    if success:
        print("RESULT: PASS - The fix works correctly!")
        print("        When Firebase is initialized but storage bucket is missing,")
        print("        a clear ValueError is raised during module import.")
    else:
        print("RESULT: FAIL - The fix did not work as expected")
        sys.exit(1)