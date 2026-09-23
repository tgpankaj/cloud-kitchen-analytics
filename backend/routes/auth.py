from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from db.connection import execute_query, execute_one
from middleware.auth import token_required

auth_bp = Blueprint('auth', __name__)


def create_token(user_id, email):
    """Generate JWT token."""
    return jwt.encode({
        'user_id': user_id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User registration."""
    data = request.get_json() or {}

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    kitchen_name = data.get('kitchen_name', '').strip()
    city = data.get('city', '').strip()

    # Validation
    errors = []
    if not email or '@' not in email:
        errors.append('Valid email required')
    if len(password) < 6:
        errors.append('Password must be at least 6 characters')
    if not kitchen_name:
        errors.append('Kitchen name required')

    if errors:
        return jsonify({'errors': errors}), 400

    # Check existing user
    existing = execute_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Hash password
    password_hash = generate_password_hash(password)

    # Insert user
    user = execute_one(
        """INSERT INTO users (email, password_hash, full_name)
           VALUES (%s, %s, %s) RETURNING id, email, full_name""",
        (email, password_hash, full_name or email.split('@')[0])
    )

    # Create default kitchen
    kitchen = execute_one(
        """INSERT INTO kitchens (user_id, name, city)
           VALUES (%s, %s, %s) RETURNING id, name, city""",
        (user['id'], kitchen_name, city or 'Unknown')
    )

    # Generate token
    token = create_token(user['id'], user['email'])

    return jsonify({
        'message': 'Account created successfully',
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name']
        },
        'kitchen': {
            'id': kitchen['id'],
            'name': kitchen['name'],
            'city': kitchen['city']
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Find user
    user = execute_one(
        """SELECT id, email, password_hash, full_name
           FROM users WHERE email = %s""",
        (email,)
    )

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Get kitchen
    kitchen = execute_one(
        """SELECT id, name, city FROM kitchens
           WHERE user_id = %s AND is_active = TRUE
           ORDER BY id LIMIT 1""",
        (user['id'],)
    )

    token = create_token(user['id'], user['email'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name']
        },
        'kitchen': {
            'id': kitchen['id'],
            'name': kitchen['name'],
            'city': kitchen['city']
        } if kitchen else None
    })


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current user info."""
    user = execute_one(
        """SELECT id, email, full_name, created_at
           FROM users WHERE id = %s""",
        (request.user_id,)
    )
    kitchens = execute_query(
        """SELECT id, name, city, is_active
           FROM kitchens WHERE user_id = %s ORDER BY id""",
        (request.user_id,)
    )

    return jsonify({
        'user': dict(user) if user else None,
        'kitchens': [dict(k) for k in kitchens]
    })


