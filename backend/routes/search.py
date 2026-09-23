"""
Global Search
Powers the topbar search
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

search_bp = Blueprint('search', __name__)


@search_bp.route('', methods=['GET'])
@search_bp.route('/', methods=['GET'])
@token_required
def search():
    q = (request.args.get('q') or '').strip()
    if not q or len(q) < 2:
        return jsonify({'results': []})

    # Get user's kitchen
    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    if not kitchen:
        return jsonify({'results': []})
    kitchen_id = kitchen['id']

    like_pattern = f"%{q}%"
    results = []

    # Search dishes
    dishes = execute_query("""
        SELECT id, name, category, selling_price
        FROM menu_items
        WHERE kitchen_id = %s
          AND name ILIKE %s
          AND is_active = TRUE
        LIMIT 5
    """, (kitchen_id, like_pattern))

    for d in dishes:
        results.append({
            'type': 'dish',
            'id': d['id'],
            'title': d['name'],
            'subtitle': d['category'] or 'Dish',
            'url': f"items.html?search={q}"
        })

    # Search customers
    customers = execute_query("""
        SELECT DISTINCT customer_phone AS phone
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone ILIKE %s
        LIMIT 5
    """, (kitchen_id, like_pattern))

    for c in customers:
        results.append({
            'type': 'customer',
            'id': c['phone'],
            'title': c['phone'],
            'subtitle': 'Customer',
            'url': f"customers.html?search={q}"
        })

    # Search orders
    orders = execute_query("""
        SELECT id, customer_phone, total_amount, order_date::text
        FROM orders
        WHERE kitchen_id = %s
          AND (customer_phone ILIKE %s OR CAST(id AS TEXT) ILIKE %s)
        ORDER BY order_date DESC
        LIMIT 5
    """, (kitchen_id, like_pattern, like_pattern))

    for o in orders:
        results.append({
            'type': 'order',
            'id': o['id'],
            'title': f"Order #ORD{o['id']:04d}",
            'subtitle': f"₹{float(o['total_amount'] or 0):,.0f} • {o['order_date']}",
            'url': f"analytics.html?order={o['id']}"
        })

    return jsonify({'results': results[:10], 'query': q})


"""
Global Search API
Powers the topbar search
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

search_bp = Blueprint('search', __name__)


@search_bp.route('', methods=['GET'])
@search_bp.route('/', methods=['GET'])
@token_required
def search():
    """
    Search across:
    - Dishes (menu_items)
    - Customers (orders.customer_phone)
    - Orders (id, phone)

    Query: ?q=query_string&limit=10
    """
    q = (request.args.get('q') or '').strip()
    limit = min(int(request.args.get('limit', 10)), 30)

    if not q or len(q) < 2:
        return jsonify({'results': [], 'query': q})

    # Get user's kitchen
    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    if not kitchen:
        return jsonify({'results': [], 'query': q})

    kitchen_id = kitchen['id']
    like_pattern = f"%{q}%"
    results = []

    # ─── Search Dishes ───
    dishes = execute_query("""
        SELECT id, name, category, selling_price
        FROM menu_items
        WHERE kitchen_id = %s
          AND name ILIKE %s
          AND is_active = TRUE
        LIMIT %s
    """, (kitchen_id, like_pattern, limit))

    for d in dishes:
        results.append({
            'type': 'dish',
            'id': d['id'],
            'title': d['name'],
            'subtitle': f"Dish · {d['category'] or 'Uncategorized'} · ₹{float(d['selling_price'] or 0):.0f}",
            'url': f"items.html?search={q}"
        })

    # ─── Search Customers ───
    customers = execute_query("""
        SELECT
            customer_phone AS phone,
            COUNT(*) AS orders,
            SUM(total_amount) AS spent
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone ILIKE %s
        GROUP BY customer_phone
        LIMIT %s
    """, (kitchen_id, like_pattern, 5))

    for c in customers:
        results.append({
            'type': 'customer',
            'id': c['phone'],
            'title': c['phone'],
            'subtitle': f"Customer · {c['orders']} orders · ₹{float(c['spent'] or 0):.0f}",
            'url': f"customers.html?phone={c['phone']}"
        })

    # ─── Search Orders ───
    orders = execute_query("""
        SELECT
            id, customer_phone, total_amount, order_date::text, status
        FROM orders
        WHERE kitchen_id = %s
          AND (
              customer_phone ILIKE %s
              OR CAST(id AS TEXT) ILIKE %s
          )
        ORDER BY id DESC
        LIMIT 5
    """, (kitchen_id, like_pattern, like_pattern))

    for o in orders:
        results.append({
            'type': 'order',
            'id': o['id'],
            'title': f"Order #ORD{o['id']:04d}",
            'subtitle': f"{o['status']} · ₹{float(o['total_amount'] or 0):,.0f} · {o['order_date']}",
            'url': f"analytics.html?order={o['id']}"
        })

    return jsonify({
        'query': q,
        'count': len(results),
        'results': results[:limit]
    })


@search_bp.route('/suggest', methods=['GET'])
@token_required
def suggest():
    """
    Quick suggestions for autocomplete.
    Lighter than full search.
    """
    q = (request.args.get('q') or '').strip()
    if not q or len(q) < 1:
        return jsonify([])

    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    if not kitchen:
        return jsonify([])

    like_pattern = f"%{q}%"

    # Combine dishes + customers
    dishes = execute_query("""
        SELECT name AS label, 'dish' AS type
        FROM menu_items
        WHERE kitchen_id = %s AND name ILIKE %s AND is_active = TRUE
        LIMIT 5
    """, (kitchen['id'], like_pattern))

    return jsonify([
        {'label': d['label'], 'type': d['type']}
        for d in dishes
    ])