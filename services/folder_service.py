from services.firebase_service import firestore_db
from models.folder import Folder
from datetime import datetime

class FolderService:
    def __init__(self):
        self.db = firestore_db
        self.collection = self.db.collection('folders')

    def create_folder(self, folder: Folder) -> Folder:
        """Create a new folder."""
        if folder.folder_id is None:
            folder_ref = self.collection.document()
            folder.folder_id = folder_ref.id
        else:
            folder_ref = self.collection.document(folder.folder_id)
        folder.UpdatedAt = datetime.utcnow()
        folder_ref.set(folder.to_dict())
        return folder

    def get_folder(self, folder_id: str) -> Optional[Folder]:
        """Get a folder by its ID."""
        folder_ref = self.collection.document(folder_id)
        folder_snapshot = folder_ref.get()
        if folder_snapshot.exists:
            return Folder.from_dict(folder_snapshot.to_dict())
        return None

    def update_folder(self, folder: Folder) -> Folder:
        """Update an existing folder."""
        if not folder.folder_id:
            raise ValueError("Folder ID is required for update")
        folder.UpdatedAt = datetime.utcnow()
        folder_ref = self.collection.document(folder.folder_id)
        folder_ref.update(folder.to_dict())
        return folder

    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder by its ID."""
        self.collection.document(folder_id).delete()

    def list_folders_by_owner(self, owner_id: str, limit: int = 50) -> List[Folder]:
        """List folders for a given owner."""
        folders = []
        query = self.collection.where('owner_id', '==', owner_id).limit(limit)
        for folder in query.stream():
            folders.append(Folder.from_dict(folder.to_dict()))
        return folders

    def list_subfolders(self, parent_id: str, limit: int = 50) -> List[Folder]:
        """List subfolders of a given parent folder."""
        folders = []
        query = self.collection.where('parent_id', '==', parent_id).limit(limit)
        for folder in query.stream():
            folders.append(Folder.from_dict(folder.to_dict()))
        return folders