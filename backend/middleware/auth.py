from functools import wraps
from flask import request, jsonify, current_app
import jwt


def token_required(f):
    """Decorator to protect routes requiring JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')

        # Also check for JSON body token
        if not token and request.is_json:
            token = request.json.get('token')

        if not token:
            return jsonify({'error': 'Authentication token missing'}), 401

        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            request.user_id = data['user_id']
            request.user_email = data.get('email', '')

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired. Please login again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated

