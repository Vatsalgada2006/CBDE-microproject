import logging
from typing import List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SecurityCenterService:
    """Scans for public links, permission vulnerabilities, and sensitive document exposure."""

    def __init__(self):
        from services.firebase_service import firestore_db
        self.db = firestore_db

    def get_security_overview(self, user_id: str) -> Dict:
        """
        Generate a full security overview for a user's document library.
        Returns scan results covering shared documents, public links, and sensitivity issues.
        """
        from services.document_service import DocumentService
        from services.share_service import ShareService

        doc_service = DocumentService()
        share_service = ShareService()
        docs = doc_service.list_documents_by_owner(user_id)

        if not docs:
            return {
                'status': 'secure',
                'risk_score': 0,
                'total_documents': 0,
                'shared_documents': [],
                'public_links': [],
                'sensitive_exposed': [],
                'recommendations': []
            }

        total = len(docs)
        shared_docs = []
        public_links = []
        sensitive_exposed = []
        recommendations = []
        risk_score = 0

        for doc in docs:
            doc_id = doc.doc_id
            shares = share_service.list_shares_for_document(doc_id)

            if not shares:
                continue

            sensitivity = getattr(doc, 'sensitivity_level', 'internal') or 'internal'
            filename = getattr(doc, 'filename', doc_id)

            for share in shares:
                is_link = getattr(share, 'is_link_share', False)
                role = getattr(share, 'role', 'viewer')
                expires = getattr(share, 'expires_at', None)

                share_info = {
                    'doc_id': doc_id,
                    'filename': filename,
                    'sensitivity': sensitivity,
                    'shared_with': getattr(share, 'shared_with_email', None) or getattr(share, 'shared_with_uid', 'Unknown'),
                    'role': role,
                    'is_link_share': is_link,
                    'expires_at': expires.isoformat() if expires else None,
                    'created_at': getattr(share, 'created_at', None)
                }

                shared_docs.append(share_info)

                if is_link:
                    public_links.append(share_info)
                    risk_score += 5

                # Check for sensitive documents being shared
                if sensitivity in ('confidential', 'restricted'):
                    sensitive_exposed.append(share_info)
                    risk_score += 15 if sensitivity == 'restricted' else 10

                    if role == 'editor':
                        risk_score += 5  # Extra risk for edit access to sensitive docs

                # Check for expired shares still active
                if expires and isinstance(expires, datetime):
                    if expires < datetime.now(timezone.utc):
                        recommendations.append(
                            f'Expired share for "{filename}" — consider revoking access'
                        )
                        risk_score += 3

        # Build recommendations
        if len(public_links) > 0:
            recommendations.append(
                f'{len(public_links)} public link(s) found — review if they are still needed'
            )
        if len(sensitive_exposed) > 0:
            recommendations.append(
                f'{len(sensitive_exposed)} sensitive document(s) are shared — verify access is appropriate'
            )
        if len(shared_docs) > total * 0.5:
            recommendations.append(
                'More than half your documents are shared — consider reviewing permissions'
            )

        # Determine status
        risk_score = min(100, risk_score)
        if risk_score >= 50:
            status = 'critical'
        elif risk_score >= 25:
            status = 'warning'
        elif risk_score > 0:
            status = 'review'
        else:
            status = 'secure'

        return {
            'status': status,
            'risk_score': risk_score,
            'total_documents': total,
            'shared_documents': shared_docs,
            'public_links': public_links,
            'sensitive_exposed': sensitive_exposed,
            'recommendations': recommendations,
            'summary': {
                'total_shared': len(shared_docs),
                'total_public_links': len(public_links),
                'total_sensitive_exposed': len(sensitive_exposed)
            }
        }
