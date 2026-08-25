import logging
from flask import Blueprint, request, jsonify, current_app
from services.firebase_service import auth, verify_firebase_token
from services.user_service import UserService
from services.audit_service import audit_service
from utils.validation import validate_email, validate_password, ValidationError, sanitize_input
from models.user import User
from functools import wraps

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
user_service = UserService()

def is_valid_email(email):
    """Basic email format validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """Basic password strength validation."""
    # At least 8 characters
    return len(password) >= 8

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        id_token = None
        # Check if the token is in the Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                id_token = auth_header[7:]  # Remove 'Bearer ' prefix
        # If not in header, check JSON body
        if not id_token and request.is_json:
            data = request.get_json()
            if data and 'id_token' in data:
                id_token = data['id_token']
        # If not in header or JSON body, check cookies
        if not id_token:
            id_token = request.cookies.get('id_token')

        if not id_token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Attach the user data to the request context for use in the route
        request.user = decoded_token
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            id_token = None
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                if auth_header.startswith('Bearer '):
                    id_token = auth_header[7:]
            if not id_token and request.is_json:
                data = request.get_json()
                if data and 'id_token' in data:
                    id_token = data['id_token']
            if not id_token:
                id_token = request.cookies.get('id_token')

            if not id_token:
                return jsonify({'error': 'Authentication token is missing'}), 401

            decoded_token = verify_firebase_token(id_token)
            if not decoded_token:
                return jsonify({'error': 'Invalid or expired token'}), 401

            uid = decoded_token['uid']
            user = user_service.get_user(uid)
            if not user:
                return jsonify({'error': 'User not found'}), 404

            if user.role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403

            request.user = decoded_token
            return f(*args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with email and password.
    Expects JSON: { "email": "user@example.com", "password": "password", "display_name": "Optional Name" }
    """
    logger.info("Register endpoint called")
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400

    email = data['email']
    password = data['password']
    display_name = data.get('display_name', email.split('@')[0])

    # Sanitize inputs
    email = sanitize_input(email, max_length=255)
    password = sanitize_input(password, max_length=128)
    display_name = sanitize_input(display_name, max_length=100)

    # Validate email format
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password strength
    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character'}), 400

    # Validate display name
    if not display_name:
        return jsonify({'error': 'Display name is required'}), 400
    if len(display_name) < 2:
        return jsonify({'error': 'Display name must be at least 2 characters long'}), 400

    try:
        # Create user in Firebase Authentication
        logger.info(f"Creating Firebase user for email: {email}")
        user_record = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=display_name,
            disabled=False
        )
        logger.info(f"Firebase user created: {user_record.uid}")

        # Create user document in Firestore
        user = User(
            uid=user_record.uid,
            email=email,
            display_name=display_name
        )
        logger.info(f"Creating user in Firestore: {user.to_dict()}")
        user_service.create_user(user)
        logger.info("User created in Firestore")

        # Audit log for user registration
        audit_log = AuditLog(
            user_id=user.uid,
            action='USER_REGISTER',
            resource_type='user',
            resource_id=user.uid,
            details=f'User registered with email: {user.email}',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)
        return jsonify({
            'message': 'User created successfully',
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name
        }), 201

    except Exception as e:
        logger.error(f"Error in register endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
def verify_token():
    """
    Verify Firebase ID token and return user data.
    Expects JSON: { "id_token": "firebase_id_token" }
    """
    from flask import make_response
    data = request.get_json()
    if not data or 'id_token' not in data:
        return jsonify({'error': 'ID token is required'}), 400

    id_token = data['id_token']
    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        return jsonify({'error': 'Invalid or expired token'}), 401

    uid = decoded_token['uid']
    # Get user from Firestore, or create if not exists
    user = user_service.get_user(uid)
    if not user:
        # Create a new user document based on the token data
        user = User(
            uid=uid,
            email=decoded_token.get('email', ''),
            display_name=decoded_token.get('name', '')
        )
        user_service.create_user(user)

    # Audit log for user login
    audit_log = AuditLog(
        user_id=uid,
        action='USER_LOGIN',
        resource_type='user',
        resource_id=uid,
        details=f'User logged in: {user.email if user else "unknown"}',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    audit_service.log_action(audit_log)
    # Set a cookie with the ID token for subsequent requests
    response = make_response(jsonify({
        'uid': user.uid,
        'email': user.email,
        'display_name': user.display_name,
        'photo_url': user.photo_url,
    }))
    # Set cookie as HttpOnly in production; for development, we may need to adjust
    # In production, we should also set Secure=True and SameSite='Lax' or 'Strict'
    secure = current_app.config.get('SESSION_COOKIE_SECURE', False)
    httponly = current_app.config.get('SESSION_COOKIE_HTTPONLY', True)
    samesite = current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
    response.set_cookie('id_token', id_token, httponly=httponly, secure=secure, samesite=samesite, max_age=60*60, path='/')  # 1 hour
    return response

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout endpoint - revoke refresh tokens for the user.
    Expects JSON: { "id_token": "firebase_id_token" } or Authorization header.
    """
    from flask import make_response
    # The token is already verified by the decorator and available in request.user
    uid = request.user['uid']
    try:
        # Audit log for user logout
        audit_log = AuditLog(
            user_id=uid,
            action='USER_LOGOUT',
            resource_type='user',
            resource_id=uid,
            details=f'User logged out: {request.user.get("email", "unknown") if request.user else "unknown"}',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        audit_service.log_action(audit_log)
        auth.revoke_refresh_tokens(uid)
        response = make_response(jsonify({'message': 'User logged out successfully'}))
        # Clear the id_token cookie
        secure = current_app.config.get('SESSION_COOKIE_SECURE', False)
        httponly = current_app.config.get('SESSION_COOKIE_HTTPONLY', True)
        samesite = current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
        response.set_cookie('id_token', '', expires=0, httponly=httponly, secure=secure, samesite=samesite)
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 400