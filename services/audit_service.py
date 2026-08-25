import logging
from firebase_admin import firestore
from config import Config
from models.audit_log import AuditLog
import uuid

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.db = firestore.client()
        self.collection = 'audit_logs'

    def log_action(self, audit_log: AuditLog):
        """Log an action to Firestore."""
        try:
            # If log_id is not provided, generate one
            if not audit_log.log_id:
                audit_log.log_id = str(uuid.uuid4())

            # Convert to dict and save
            doc_ref = self.db.collection(self.collection).document(audit_log.log_id)
            doc_ref.set(audit_log.to_dict())
            logger.info(f"Audit log saved: {audit_log.log_id} - {audit_log.action}")
            return audit_log.log_id
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
            raise

# Create a singleton instance
audit_service = AuditService()
