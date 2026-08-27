from flask import Blueprint, request, jsonify
import logging
from routes.auth import token_required

logger = logging.getLogger(__name__)

health_center_bp = Blueprint('health_center', __name__)

def get_health_score_service():
    from services.health_score_service import HealthScoreService
    return HealthScoreService()

def get_security_center_service():
    from services.security_center_service import SecurityCenterService
    return SecurityCenterService()

@health_center_bp.route('/score', methods=['GET'])
@token_required
def get_health_score():
    """Get the overall health score and details for the user's library."""
    try:
        user_id = request.user['uid']
        health_service = get_health_score_service()
        score_data = health_service.compute_health(user_id)
        return jsonify(score_data), 200
    except Exception as e:
        logger.error(f"Error computing health score: {e}")
        return jsonify({'error': str(e)}), 500

@health_center_bp.route('/security', methods=['GET'])
@token_required
def get_security_overview():
    """Get the security status and potential risks for the user's library."""
    try:
        user_id = request.user['uid']
        security_service = get_security_center_service()
        security_data = security_service.get_security_overview(user_id)
        return jsonify(security_data), 200
    except Exception as e:
        logger.error(f"Error getting security overview: {e}")
        return jsonify({'error': str(e)}), 500

@health_center_bp.route('/activity', methods=['GET'])
@token_required
def get_activity_timeline():
    """Get the chronological audit trail for the user."""
    try:
        user_id = request.user['uid']
        limit = int(request.args.get('limit', 50))
        
        from services.audit_service import audit_service
        logs = audit_service.get_user_audit_logs(user_id, limit=limit)
        
        # Format the logs for frontend consumption
        formatted_logs = []
        for log in logs:
            log_dict = log.to_dict()
            if log.created_at:
                log_dict['created_at_iso'] = log.created_at.isoformat()
                log_dict['created_at_human'] = log.created_at.strftime("%b %d, %Y %I:%M %p")
            formatted_logs.append(log_dict)
            
        return jsonify({
            'activities': formatted_logs,
            'total_returned': len(formatted_logs)
        }), 200
    except Exception as e:
        logger.error(f"Error getting activity timeline: {e}")
        return jsonify({'error': str(e)}), 500
