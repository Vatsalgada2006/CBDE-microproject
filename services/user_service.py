from services.firebase_service import firestore_db
from models.user import User

class UserService:
    def __init__(self):
        self.db = firestore_db
        self.collection = self.db.collection('users')

    def create_user(self, user: User):
        """Create a new user in Firestore."""
        user_ref = self.collection.document(user.uid)
        user_ref.set(user.to_dict())
        return user

    def get_user(self, uid):
        """Get a user by UID."""
        user_doc = self.collection.document(uid).get()
        if user_doc.exists:
            return User.from_dict(user_doc.to_dict())
        return None

    def update_user(self, user: User):
        """Update an existing user."""
        user_ref = self.collection.document(user.uid)
        user_ref.update(user.to_dict())
        return user

    def delete_user(self, uid):
        """Delete a user by UID."""
        self.collection.document(uid).delete()
