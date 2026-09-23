"""
Razorpay Payment Routes
"""
from flask import Blueprint, request, jsonify, current_app
from middleware.auth import token_required
from db.connection import execute_query, execute_one
import razorpay 
import hmac
import hashlib

payments_bp = Blueprint('payments', __name__)

PLANS = {
    'starter': {'amount': 49900, 'name': 'Starter', 'days': 30},   # ₹499 in paise
    'pro': {'amount': 149900, 'name': 'Pro', 'days': 30},          # ₹1,499
    'business': {'amount': 399900, 'name': 'Business', 'days': 30},# ₹3,999
}


def get_razorpay_client():
    return razorpay.Client(
        auth=(
            current_app.config['RAZORPAY_KEY_ID'],
            current_app.config['RAZORPAY_KEY_SECRET']
        )
    )


@payments_bp.route('/plans', methods=['GET'])
def get_plans():
    """Return available plans."""
    return jsonify([
        {'id': k, 'name': v['name'], 'amount': v['amount'] / 100, 'days': v['days']}
        for k, v in PLANS.items()
    ])


@payments_bp.route('/create-order', methods=['POST'])
@token_required
def create_order():
    """Create Razorpay order."""
    data = request.get_json() or {}
    plan_id = data.get('plan')

    if plan_id not in PLANS:
        return jsonify({'error': 'Invalid plan'}), 400

    plan = PLANS[plan_id]

    try:
        client = get_razorpay_client()
        order = client.order.create({
            'amount': plan['amount'],
            'currency': 'INR',
            'receipt': f'user_{request.user_id}_{plan_id}',
            'notes': {
                'user_id': request.user_id,
                'plan': plan_id
            }
        })

        return jsonify({
            'order_id': order['id'],
            'amount': plan['amount'],
            'currency': 'INR',
            'plan': plan_id,
            'plan_name': plan['name'],
            'key_id': current_app.config['RAZORPAY_KEY_ID']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/verify', methods=['POST'])
@token_required
def verify_payment():
    """Verify Razorpay signature and activate subscription."""
    data = request.get_json() or {}

    order_id = data.get('razorpay_order_id')
    payment_id = data.get('razorpay_payment_id')
    signature = data.get('razorpay_signature')
    plan_id = data.get('plan')

    if not all([order_id, payment_id, signature, plan_id]):
        return jsonify({'error': 'Missing payment fields'}), 400

    if plan_id not in PLANS:
        return jsonify({'error': 'Invalid plan'}), 400

    # Verify signature
    key_secret = current_app.config['RAZORPAY_KEY_SECRET']
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        key_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected != signature:
        return jsonify({'error': 'Invalid signature'}), 400

    # Activate subscription
    plan = PLANS[plan_id]
    execute_query("""
        INSERT INTO subscriptions
        (user_id, plan, status, razorpay_order_id, razorpay_payment_id,
         amount, expires_at)
        VALUES (%s, %s, 'active', %s, %s, %s,
                NOW() + INTERVAL '%s days')
    """, (
        request.user_id, plan_id, order_id, payment_id,
        plan['amount'] / 100, plan['days']
    ), fetch=False)

    return jsonify({
        'message': 'Payment verified',
        'plan': plan_id,
        'status': 'active'
    })


@payments_bp.route('/my-subscription', methods=['GET'])
@token_required
def my_subscription():
    """Get current subscription."""
    sub = execute_one("""
        SELECT plan, status, started_at, expires_at
        FROM subscriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (request.user_id,))

    if not sub:
        return jsonify({'plan': 'trial', 'status': 'active', 'trial': True})

    return jsonify({
        'plan': sub['plan'],
        'status': sub['status'],
        'started_at': str(sub['started_at']),
        'expires_at': str(sub['expires_at'])
    })