"""
Branches / Kitchens Routes
Updated for KitchenIQ UI — sidebar kitchen selector
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

branches_bp = Blueprint('branches', __name__)


def verify_kitchen_access(kitchen_id, user_id):
    """Check if kitchen belongs to user."""
    k = execute_one(
        "SELECT id FROM kitchens WHERE id = %s AND user_id = %s",
        (kitchen_id, user_id)
    )
    return bool(k)


def get_date_range(request):
    """Extract days filter (default 30)."""
    days = request.args.get('days', '30')
    if days == 'all':
        return None
    try:
        return int(days)
    except ValueError:
        return 30


def build_date_filter(days, alias='o'):
    """Build SQL date filter."""
    if days is None:
        return "", []
    return f"AND {alias}.order_date >= CURRENT_DATE - INTERVAL '%s days'", [days]


# ==========================================
# LIST KITCHENS (Shell kitchen selector)
# ==========================================
@branches_bp.route('/list', methods=['GET'])
@token_required
def list_branches():
    """
    Simple list for the shell kitchen selector.
    Returns only active kitchens for the current user.
    """
    rows = execute_query("""
        SELECT id, name, city, is_active
        FROM kitchens
        WHERE user_id = %s
        ORDER BY is_active DESC, id ASC
    """, (request.user_id,))

    return jsonify([{
        'id': r['id'],
        'name': r['name'],
        'city': r['city'] or '',
        'is_active': bool(r['is_active'])
    } for r in rows])


# ==========================================
# CREATE KITCHEN
# ==========================================
@branches_bp.route('/create', methods=['POST'])
@token_required
def create_branch():
    """Add a new kitchen (max 5 per user)."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return jsonify({'error': 'Kitchen name required'}), 400

    # Limit check
    count = execute_one(
        "SELECT COUNT(*) AS c FROM kitchens WHERE user_id = %s",
        (request.user_id,)
    )
    if count and count['c'] >= 5:
        return jsonify({'error': 'Maximum 5 kitchens allowed'}), 400

    # Duplicate check
    existing = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s AND LOWER(name) = LOWER(%s)",
        (request.user_id, name)
    )
    if existing:
        return jsonify({'error': 'Kitchen with this name already exists'}), 409

    result = execute_one("""
        INSERT INTO kitchens (user_id, name, city, address)
        VALUES (%s, %s, %s, %s)
        RETURNING id, name, city
    """, (
        request.user_id,
        name,
        data.get('city', '').strip() or None,
        data.get('address', '').strip() or None
    ))

    return jsonify({
        'message': 'Kitchen created successfully',
        'kitchen': {
            'id': result['id'],
            'name': result['name'],
            'city': result['city'] or ''
        }
    }), 201


# ==========================================
# GET SINGLE KITCHEN
# ==========================================
@branches_bp.route('/<int:kitchen_id>', methods=['GET'])
@token_required
def get_branch(kitchen_id):
    """Get single kitchen details."""
    if not verify_kitchen_access(kitchen_id, request.user_id):
        return jsonify({'error': 'Kitchen not found'}), 404

    k = execute_one("""
        SELECT id, name, city, address, is_active, created_at::text
        FROM kitchens WHERE id = %s
    """, (kitchen_id,))

    return jsonify({
        'id': k['id'],
        'name': k['name'],
        'city': k['city'] or '',
        'address': k['address'] or '',
        'is_active': bool(k['is_active']),
        'created_at': k['created_at']
    })


# ==========================================
# UPDATE KITCHEN
# ==========================================
@branches_bp.route('/<int:kitchen_id>', methods=['PUT'])
@token_required
def update_branch(kitchen_id):
    """Update kitchen details."""
    if not verify_kitchen_access(kitchen_id, request.user_id):
        return jsonify({'error': 'Kitchen not found'}), 404

    data = request.get_json() or {}

    execute_query("""
        UPDATE kitchens SET
            name = COALESCE(%s, name),
            city = COALESCE(%s, city),
            address = COALESCE(%s, address),
            is_active = COALESCE(%s, is_active)
        WHERE id = %s AND user_id = %s
    """, (
        data.get('name'),
        data.get('city'),
        data.get('address'),
        data.get('is_active'),
        kitchen_id,
        request.user_id
    ), fetch=False)

    return jsonify({'message': 'Kitchen updated successfully'})


# ==========================================
# DELETE KITCHEN
# ==========================================
@branches_bp.route('/<int:kitchen_id>', methods=['DELETE'])
@token_required
def delete_branch(kitchen_id):
    """Delete kitchen (only if no orders)."""
    if not verify_kitchen_access(kitchen_id, request.user_id):
        return jsonify({'error': 'Kitchen not found'}), 404

    # Safety check
    orders = execute_one(
        "SELECT COUNT(*) AS c FROM orders WHERE kitchen_id = %s",
        (kitchen_id,)
    )
    if orders and orders['c'] > 0:
        return jsonify({
            'error': f"Cannot delete. Kitchen has {orders['c']} orders. Deactivate instead."
        }), 400

    execute_query(
        "DELETE FROM kitchens WHERE id = %s AND user_id = %s",
        (kitchen_id, request.user_id),
        fetch=False
    )

    return jsonify({'message': 'Kitchen deleted successfully'})


# ==========================================
# COMPARE KITCHENS (Branches page)
# ==========================================
@branches_bp.route('/compare', methods=['GET'])
@token_required
def compare_branches():
    """Side-by-side kitchen comparison."""
    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            k.id,
            k.name,
            k.city,
            k.is_active,
            COALESCE(o.total_orders, 0) AS total_orders,
            COALESCE(o.gross_revenue, 0) AS gross_revenue,
            COALESCE(o.net_revenue, 0) AS net_revenue,
            COALESCE(o.commission_paid, 0) AS commission_paid,
            COALESCE(o.avg_order_value, 0) AS avg_order_value,
            COALESCE(o.unique_customers, 0) AS unique_customers,
            COALESCE(o.avg_delivery_time, 0) AS avg_delivery_time,
            COALESCE(o.cancel_rate, 0) AS cancel_rate
        FROM kitchens k
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) AS total_orders,
                SUM(o.total_amount) AS gross_revenue,
                SUM(o.total_amount * (1 - o.commission_pct/100.0)) AS net_revenue,
                SUM(o.total_amount * o.commission_pct/100.0) AS commission_paid,
                AVG(o.total_amount) AS avg_order_value,
                COUNT(DISTINCT o.customer_phone)
                    FILTER (WHERE o.customer_phone IS NOT NULL) AS unique_customers,
                AVG(o.delivery_time_minutes) AS avg_delivery_time,
                (COUNT(*) FILTER (WHERE o.status = 'cancelled')::float
                    / NULLIF(COUNT(*), 0) * 100) AS cancel_rate
            FROM orders o
            WHERE o.kitchen_id = k.id
              {date_sql}
        ) o ON TRUE
        WHERE k.user_id = %s
        ORDER BY COALESCE(o.net_revenue, 0) DESC
    """

    params = date_params + [request.user_id]
    rows = execute_query(sql, params)

    return jsonify([{
        'id': r['id'],
        'name': r['name'],
        'city': r['city'] or '',
        'is_active': bool(r['is_active']),
        'total_orders': int(r['total_orders'] or 0),
        'gross_revenue': round(float(r['gross_revenue'] or 0), 2),
        'net_revenue': round(float(r['net_revenue'] or 0), 2),
        'commission_paid': round(float(r['commission_paid'] or 0), 2),
        'avg_order_value': round(float(r['avg_order_value'] or 0), 2),
        'unique_customers': int(r['unique_customers'] or 0),
        'avg_delivery_time': round(float(r['avg_delivery_time'] or 0), 1),
        'cancel_rate': round(float(r['cancel_rate'] or 0), 1)
    } for r in rows])


# ==========================================
# CONSOLIDATED (All kitchens combined)
# ==========================================
@branches_bp.route('/consolidated', methods=['GET'])
@token_required
def consolidated():
    """Combined analytics across all kitchens."""
    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    kpis = execute_one(f"""
        SELECT
            COUNT(DISTINCT k.id) AS total_kitchens,
            COUNT(DISTINCT o.id) AS total_orders,
            COALESCE(SUM(o.total_amount), 0) AS gross_revenue,
            COALESCE(SUM(o.total_amount * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(AVG(o.total_amount), 0) AS avg_order_value,
            COUNT(DISTINCT o.customer_phone)
                FILTER (WHERE o.customer_phone IS NOT NULL) AS unique_customers
        FROM kitchens k
        LEFT JOIN orders o ON o.kitchen_id = k.id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE k.user_id = %s
    """, date_params + [request.user_id])

    return jsonify({
        'total_kitchens': int(kpis['total_kitchens'] or 0),
        'total_orders': int(kpis['total_orders'] or 0),
        'gross_revenue': round(float(kpis['gross_revenue'] or 0), 2),
        'net_revenue': round(float(kpis['net_revenue'] or 0), 2),
        'avg_order_value': round(float(kpis['avg_order_value'] or 0), 2),
        'unique_customers': int(kpis['unique_customers'] or 0)
    })

