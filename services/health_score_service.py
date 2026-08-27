import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HealthScoreService:
    """Computes metadata completeness rates and identifies library issues."""

    def __init__(self):
        from services.firebase_service import firestore_db
        self.db = firestore_db

    def compute_health(self, user_id: str) -> Dict:
        """
        Compute a comprehensive health score for a user's document library.
        Returns a dict with score (0-100), category scores, and specific issues.
        """
        from services.document_service import DocumentService
        doc_service = DocumentService()
        docs = doc_service.list_documents_by_owner(user_id)

        if not docs:
            return {
                'overall_score': 100,
                'total_documents': 0,
                'categories': {},
                'issues': [],
                'recommendations': ['Upload your first document to get started!']
            }

        total = len(docs)
        issues = []
        recommendations = []

        # --- Metadata Completeness ---
        missing_titles = [d for d in docs if not getattr(d, 'title', None)]
        missing_tags = [d for d in docs if not getattr(d, 'tags', None) or len(d.tags) == 0]
        missing_type = [d for d in docs if not getattr(d, 'document_type', None)]
        missing_sensitivity = [d for d in docs if not getattr(d, 'sensitivity_level', None)]

        title_pct = round((1 - len(missing_titles) / total) * 100)
        tags_pct = round((1 - len(missing_tags) / total) * 100)
        type_pct = round((1 - len(missing_type) / total) * 100)
        sensitivity_pct = round((1 - len(missing_sensitivity) / total) * 100)
        metadata_score = round((title_pct + tags_pct + type_pct + sensitivity_pct) / 4)

        if len(missing_titles) > 0:
            issues.append({
                'type': 'missing_title',
                'severity': 'warning',
                'count': len(missing_titles),
                'message': f'{len(missing_titles)} documents are missing a title'
            })
        if len(missing_tags) > 0:
            issues.append({
                'type': 'missing_tags',
                'severity': 'info',
                'count': len(missing_tags),
                'message': f'{len(missing_tags)} documents have no tags'
            })

        # --- Processing Status ---
        pending = [d for d in docs if getattr(d, 'processing_status', 'pending') == 'pending']
        failed = [d for d in docs if getattr(d, 'processing_status', '') == 'failed']
        completed = [d for d in docs if getattr(d, 'processing_status', '') == 'completed']

        processing_score = round((len(completed) / total) * 100) if total > 0 else 100

        if len(failed) > 0:
            issues.append({
                'type': 'processing_failed',
                'severity': 'error',
                'count': len(failed),
                'message': f'{len(failed)} documents failed processing'
            })
        if len(pending) > 0:
            issues.append({
                'type': 'processing_pending',
                'severity': 'info',
                'count': len(pending),
                'message': f'{len(pending)} documents still pending AI analysis'
            })

        # --- Suggestions Pending ---
        pending_suggestions = [d for d in docs if getattr(d, 'suggestions_status', '') == 'pending']
        if len(pending_suggestions) > 0:
            issues.append({
                'type': 'pending_suggestions',
                'severity': 'info',
                'count': len(pending_suggestions),
                'message': f'{len(pending_suggestions)} documents have unreviewed AI suggestions'
            })
            recommendations.append(f'Review {len(pending_suggestions)} pending suggestions in your AI Inbox')

        # --- Sensitivity Audit ---
        restricted_docs = [d for d in docs if getattr(d, 'sensitivity_level', '') == 'restricted']
        confidential_docs = [d for d in docs if getattr(d, 'sensitivity_level', '') == 'confidential']

        security_score = 100
        if len(restricted_docs) > 0:
            recommendations.append(f'{len(restricted_docs)} restricted documents detected — verify sharing settings')
            # Check if any restricted docs are shared
            from services.share_service import ShareService
            share_service = ShareService()
            for doc in restricted_docs:
                shares = share_service.list_shares_for_document(doc.doc_id)
                if shares:
                    security_score -= 15
                    issues.append({
                        'type': 'restricted_shared',
                        'severity': 'error',
                        'count': 1,
                        'message': f'Restricted document "{getattr(doc, "filename", doc.doc_id)}" is shared with others'
                    })

        # --- Overall Score ---
        overall = round((metadata_score * 0.4 + processing_score * 0.3 + security_score * 0.3))
        overall = max(0, min(100, overall))

        # Build recommendations
        if len(missing_titles) > 3:
            recommendations.append('Accept AI-suggested titles to improve discoverability')
        if len(missing_tags) > 3:
            recommendations.append('Add tags to your documents for better organization')

        return {
            'overall_score': overall,
            'total_documents': total,
            'categories': {
                'metadata_completeness': {
                    'score': metadata_score,
                    'details': {
                        'titles': title_pct,
                        'tags': tags_pct,
                        'types': type_pct,
                        'sensitivity': sensitivity_pct
                    }
                },
                'processing': {
                    'score': processing_score,
                    'completed': len(completed),
                    'pending': len(pending),
                    'failed': len(failed)
                },
                'security': {
                    'score': security_score
                }
            },
            'issues': issues,
            'recommendations': recommendations
        }
