import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from services.firebase_service import firestore_db, storage_bucket, _firebase_initialized

logger = logging.getLogger(__name__)


class HealthService:
    """Unified dependency check and connectivity test service for IntelliDoc."""

    def __init__(self):
        self.db = firestore_db
        self.bucket = storage_bucket

    def check_firestore(self) -> Dict[str, Any]:
        """
        Tests Firestore connectivity by attempting a simple read.
        Returns: {'status': 'ok'|'mock'|'error', 'latency_ms': float, 'error': str|None}
        """
        start_time = time.time()
        try:
            if not _firebase_initialized:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    'status': 'mock',
                    'latency_ms': latency_ms,
                    'error': None
                }

            # Attempt a simple read operation from Firestore
            list(self.db.collection('documents').limit(1).stream())
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                'status': 'ok',
                'latency_ms': latency_ms,
                'error': None
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Firestore health check failed: {e}")
            return {
                'status': 'error',
                'latency_ms': latency_ms,
                'error': str(e)
            }

    def check_storage(self) -> Dict[str, Any]:
        """
        Tests Firebase Storage by checking bucket existence.
        Returns: {'status': 'ok'|'mock'|'error', 'latency_ms': float, 'error': str|None}
        """
        start_time = time.time()
        try:
            if not _firebase_initialized:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    'status': 'mock',
                    'latency_ms': latency_ms,
                    'error': None
                }

            if self.bucket is None:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    'status': 'error',
                    'latency_ms': latency_ms,
                    'error': 'Storage bucket is not configured'
                }

            exists = self.bucket.exists()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            if not exists:
                return {
                    'status': 'error',
                    'latency_ms': latency_ms,
                    'error': 'Storage bucket does not exist or is inaccessible'
                }

            return {
                'status': 'ok',
                'latency_ms': latency_ms,
                'error': None
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Storage health check failed: {e}")
            return {
                'status': 'error',
                'latency_ms': latency_ms,
                'error': str(e)
            }

    def check_intelligence(self) -> Dict[str, Any]:
        """
        Checks if the intelligence service (sentence-transformers model) is loaded.
        Returns: {'status': 'ok'|'error', 'model_loaded': bool, 'error': str|None}
        """
        try:
            from services.intelligence_service import IntelligenceService
            intelligence_svc = IntelligenceService()

            model_loaded = False
            if hasattr(intelligence_svc, 'model') and intelligence_svc.model is not None:
                model_loaded = True
            elif hasattr(intelligence_svc, '_embedding_service') and intelligence_svc._embedding_service is not None:
                model_loaded = getattr(intelligence_svc._embedding_service, 'model', None) is not None
            elif hasattr(intelligence_svc, 'embedding_service'):
                emb_svc = getattr(intelligence_svc, 'embedding_service', None)
                if emb_svc is not None:
                    model_loaded = getattr(emb_svc, 'model', None) is not None

            return {
                'status': 'ok',
                'model_loaded': model_loaded,
                'error': None
            }
        except Exception as e:
            logger.error(f"Intelligence service health check failed: {e}")
            return {
                'status': 'error',
                'model_loaded': False,
                'error': str(e)
            }

    def check_disk_space(self) -> Dict[str, Any]:
        """
        Checks available disk space.
        Returns: {'status': 'ok'|'warning'|'error', 'free_mb': float}
        """
        try:
            try:
                import psutil
                disk_usage = psutil.disk_usage(os.getcwd())
                free_bytes = disk_usage.free
            except ImportError:
                import shutil
                disk_usage = shutil.disk_usage(os.getcwd())
                free_bytes = disk_usage.free

            free_mb = round(free_bytes / (1024 * 1024), 2)

            # Thresholds: < 100MB is error, < 500MB is warning
            if free_mb < 100:
                status = 'error'
            elif free_mb < 500:
                status = 'warning'
            else:
                status = 'ok'

            return {
                'status': status,
                'free_mb': free_mb
            }
        except Exception as e:
            logger.error(f"Disk space health check failed: {e}")
            return {
                'status': 'error',
                'free_mb': 0.0
            }

    def check_memory(self) -> Dict[str, Any]:
        """
        Checks process memory usage.
        Returns: {'status': 'ok'|'warning'|'error', 'used_mb': float, 'percent': float}
        """
        try:
            try:
                import psutil
                process = psutil.Process(os.getpid())
                mem_info = process.memory_info()
                used_mb = round(mem_info.rss / (1024 * 1024), 2)
                percent = round(process.memory_percent(), 2)
            except ImportError:
                used_mb = 0.0
                percent = 0.0

            # Thresholds: > 90% is error, > 75% is warning
            if percent > 90.0:
                status = 'error'
            elif percent > 75.0:
                status = 'warning'
            else:
                status = 'ok'

            return {
                'status': status,
                'used_mb': used_mb,
                'percent': percent
            }
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")
            return {
                'status': 'error',
                'used_mb': 0.0,
                'percent': 0.0
            }

    def check_all(self) -> Dict[str, Any]:
        """
        Runs all health checks and returns a summary dict.
        Returns: {
            'status': 'healthy'|'degraded'|'unhealthy',
            'checks': dict of individual check results,
            'timestamp': ISO 8601 string
        }
        """
        checks = {
            'firestore': self.check_firestore(),
            'storage': self.check_storage(),
            'intelligence': self.check_intelligence(),
            'disk_space': self.check_disk_space(),
            'memory': self.check_memory()
        }

        # Determine overall health status
        statuses = [check.get('status') for check in checks.values() if isinstance(check, dict)]

        # Critical checks failure marks system as unhealthy
        critical_checks = ['firestore', 'storage', 'memory']
        if any(checks.get(k, {}).get('status') == 'error' for k in critical_checks):
            overall_status = 'unhealthy'
        elif 'error' in statuses or 'warning' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'

        return {
            'status': overall_status,
            'checks': checks,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
