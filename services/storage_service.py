from services.firebase_service import storage_bucket
import uuid
from mimetypes import guess_type

class StorageService:
    def __init__(self):
        self.bucket = storage_bucket

    def upload_file(self, file_data, filename, content_type=None):
        """
        Upload a file to Firebase Storage.
        Returns the public download URL (or a mock URL in development).
        """
        # Generate a unique filename to avoid collisions
        file_extension = filename.split('.')[-1] if '.' in filename else ''
        unique_filename = f"{uuid.uuid4().hex}"
        if file_extension:
            unique_filename += f".{file_extension}"
        
        # Determine the storage path (e.g., uploads/{unique_filename})
        blob_path = f"uploads/{unique_filename}"
        blob = self.bucket.blob(blob_path)
        
        # Upload the file
        if isinstance(file_data, bytes):
            blob.upload_from_string(file_data, content_type=content_type)
        else:
            # Assume it's a file-like object
            blob.upload_from_file(file_data)
        
        # Make the blob publicly accessible (if needed) or generate a signed URL
        # For simplicity, we'll generate a signed URL that expires in 1 hour.
        # In production, you might want to set proper security rules.
        url = blob.generate_signed_url(expiration=3600, method="GET")
        return url, blob_path

    def delete_file(self, blob_path):
        """
        Delete a file from Firebase Storage given its blob path.
        """
        blob = self.bucket.blob(blob_path)
        blob.delete()
