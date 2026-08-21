from flask import Blueprint, request, jsonify
from services.firebase_service import auth, verify_firebase_token
from services.user_service import UserService
from models.user import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)
user_service = UserService()

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
        
        if not id_token:
            return jsonify({'error': 'Authentication token is missing'}), 401
        
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Attach the user data to the request context for use in the route
        request.user = decoded_token
        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with email and password.
    Expects JSON: { "email": "user@example.com", "password": "password", "display_name": "Optional Name" }
    """
    print("Register endpoint called")  # Debug print
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400

    email = data['email']
    password = data['password']
    display_name = data.get('display_name', email.split('@')[0])

    try:
        # Create user in Firebase Authentication
        print(f"Creating Firebase user for email: {email}")  # Debug print
        user_record = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=display_name,
            disabled=False
        )
        print(f"Firebase user created: {user_record.uid}")  # Debug print

        # Create user document in Firestore
        user = User(
            uid=user_record.uid,
            email=email,
            display_name=display_name
        )
        print(f"Creating user in Firestore: {user.to_dict()}")  # Debug print
        user_service.create_user(user)
        print(f"User created in Firestore")  # Debug print

        return jsonify({
            'message': 'User created successfully',
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name
        }), 201

    except Exception as e:
        print(f"Error in register endpoint: {e}")  # Debug print
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Verify Firebase ID token and return user data.
    Expects JSON: { "id_token": "firebase_id_token" }
    """
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

    return jsonify({
        'uid': user.uid,
        'email': user.email,
        'display_name': user.display_name,
        'photo_url': user.photo_url
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout endpoint - revoke refresh tokens for the user.
    Expects JSON: { "id_token": "firebase_id_token" } or Authorization header.
    """
    # The token is already verified by the decorator and available in request.user
    uid = request.user['uid']
    try:
        auth.revoke_refresh_tokens(uid)
        return jsonify({'message': 'User logged out successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
