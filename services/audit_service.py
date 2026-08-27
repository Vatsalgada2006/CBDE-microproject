import logging
from services.firebase_service import firestore_db
from models.audit_log import AuditLog
import uuid

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.db = firestore_db
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

    def get_user_audit_logs(self, user_id: str, limit: int = 50):
        """Retrieve recent audit logs for a specific user."""
        try:
            query = self.db.collection(self.collection)\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction='DESCENDING')\
                .limit(limit)
            
            logs = []
            for doc in query.stream():
                data = doc.to_dict()
                # Handle Firestore datetime mapping
                if 'created_at' in data and hasattr(data['created_at'], 'timestamp'):
                    from datetime import datetime, timezone
                    data['created_at'] = datetime.fromtimestamp(data['created_at'].timestamp(), tz=timezone.utc)
                logs.append(AuditLog.from_dict(data))
            
            return logs
        except Exception as e:
            logger.error(f"Failed to fetch audit logs for user {user_id}: {e}")
            # If index is missing, fallback to client-side sort
            if 'index' in str(e).lower():
                logger.warning("Falling back to client-side sorting due to missing index")
                query = self.db.collection(self.collection).where('user_id', '==', user_id).stream()
                logs = []
                for doc in query:
                    data = doc.to_dict()
                    if 'created_at' in data and hasattr(data['created_at'], 'timestamp'):
                        from datetime import datetime, timezone
                        data['created_at'] = datetime.fromtimestamp(data['created_at'].timestamp(), tz=timezone.utc)
                    logs.append(AuditLog.from_dict(data))
                
                logs.sort(key=lambda x: x.created_at, reverse=True)
                return logs[:limit]
            return []

# Create a singleton instance
audit_service = AuditService()
