"""
Food Cost Analysis Routes
Ingredients, recipes, true profitability, stock alerts.
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one, get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor

foodcost_bp = Blueprint('foodcost', __name__)


def get_kitchen_id(request):
    kitchen_id = request.args.get('kitchen_id')
    if kitchen_id:
        try:
            return int(kitchen_id)
        except (ValueError, TypeError):
            pass

    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    return kitchen['id'] if kitchen else None


def verify_kitchen_access(kitchen_id, user_id):
    """Check kitchen belongs to user."""
    k = execute_one(
        "SELECT id FROM kitchens WHERE id = %s AND user_id = %s",
        (kitchen_id, user_id)
    )
    return bool(k)


# ==========================================
# ENDPOINT 1: Ingredients CRUD
# ==========================================
@foodcost_bp.route('/ingredients', methods=['GET'])
@token_required
def list_ingredients():
    """List all ingredients for kitchen."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query("""
        SELECT id, name, unit, cost_per_unit, current_stock,
               reorder_threshold,
               (current_stock <= reorder_threshold) AS needs_reorder,
               created_at
        FROM ingredients
        WHERE kitchen_id = %s
        ORDER BY name
    """, (kitchen_id,))

    return jsonify([{
        'id': r['id'],
        'name': r['name'],
        'unit': r['unit'] or 'kg',
        'cost_per_unit': float(r['cost_per_unit'] or 0),
        'current_stock': float(r['current_stock'] or 0),
        'reorder_threshold': float(r['reorder_threshold'] or 0),
        'needs_reorder': bool(r['needs_reorder']),
        'stock_value': round(float(r['current_stock'] or 0) * float(r['cost_per_unit'] or 0), 2)
    } for r in rows])


@foodcost_bp.route('/ingredients', methods=['POST'])
@token_required
def create_ingredient():
    """Add new ingredient."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    if not verify_kitchen_access(kitchen_id, request.user_id):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Ingredient name required'}), 400

    # Check duplicate
    existing = execute_one(
        "SELECT id FROM ingredients WHERE kitchen_id = %s AND LOWER(name) = LOWER(%s)",
        (kitchen_id, name)
    )
    if existing:
        return jsonify({'error': 'Ingredient already exists'}), 409

    result = execute_one("""
        INSERT INTO ingredients
        (kitchen_id, name, unit, cost_per_unit, current_stock, reorder_threshold)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name
    """, (
        kitchen_id,
        name,
        data.get('unit', 'kg'),
        float(data.get('cost_per_unit', 0)),
        float(data.get('current_stock', 0)),
        float(data.get('reorder_threshold', 0))
    ))

    return jsonify({
        'message': 'Ingredient created',
        'id': result['id'],
        'name': result['name']
    }), 201


@foodcost_bp.route('/ingredients/<int:ingredient_id>', methods=['PUT'])
@token_required
def update_ingredient(ingredient_id):
    """Update ingredient."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    # Verify ownership
    ing = execute_one(
        "SELECT id FROM ingredients WHERE id = %s AND kitchen_id = %s",
        (ingredient_id, kitchen_id)
    )
    if not ing:
        return jsonify({'error': 'Ingredient not found'}), 404

    data = request.get_json() or {}

    execute_query("""
        UPDATE ingredients SET
            name = COALESCE(%s, name),
            unit = COALESCE(%s, unit),
            cost_per_unit = COALESCE(%s, cost_per_unit),
            current_stock = COALESCE(%s, current_stock),
            reorder_threshold = COALESCE(%s, reorder_threshold)
        WHERE id = %s
    """, (
        data.get('name'),
        data.get('unit'),
        data.get('cost_per_unit'),
        data.get('current_stock'),
        data.get('reorder_threshold'),
        ingredient_id
    ), fetch=False)

    return jsonify({'message': 'Ingredient updated'})


@foodcost_bp.route('/ingredients/<int:ingredient_id>', methods=['DELETE'])
@token_required
def delete_ingredient(ingredient_id):
    """Delete ingredient."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    ing = execute_one(
        "SELECT id FROM ingredients WHERE id = %s AND kitchen_id = %s",
        (ingredient_id, kitchen_id)
    )
    if not ing:
        return jsonify({'error': 'Ingredient not found'}), 404

    # Check if used in recipes
    usage = execute_one(
        "SELECT COUNT(*) AS count FROM recipes WHERE ingredient_id = %s",
        (ingredient_id,)
    )
    if usage and usage['count'] > 0:
        return jsonify({
            'error': f"Cannot delete. Used in {usage['count']} recipes."
        }), 400

    execute_query(
        "DELETE FROM ingredients WHERE id = %s",
        (ingredient_id,),
        fetch=False
    )

    return jsonify({'message': 'Ingredient deleted'})


# ==========================================
# ENDPOINT 2: Recipes CRUD
# ==========================================
@foodcost_bp.route('/recipes/<int:menu_item_id>', methods=['GET'])
@token_required
def get_recipe(menu_item_id):
    """Get recipe for a menu item with calculated costs."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    # Get menu item
    item = execute_one("""
        SELECT id, name, cost_price, selling_price
        FROM menu_items
        WHERE id = %s AND kitchen_id = %s
    """, (menu_item_id, kitchen_id))

    if not item:
        return jsonify({'error': 'Menu item not found'}), 404

    # Get recipe ingredients
    rows = execute_query("""
        SELECT
            r.id,
            r.quantity_required,
            i.id AS ingredient_id,
            i.name AS ingredient_name,
            i.unit,
            i.cost_per_unit,
            (r.quantity_required * i.cost_per_unit) AS line_cost
        FROM recipes r
        JOIN ingredients i ON i.id = r.ingredient_id
        WHERE r.menu_item_id = %s
        ORDER BY i.name
    """, (menu_item_id,))

    total_cost = sum(float(r['line_cost'] or 0) for r in rows)

    return jsonify({
        'menu_item': {
            'id': item['id'],
            'name': item['name'],
            'cost_price': float(item['cost_price'] or 0),
            'selling_price': float(item['selling_price'] or 0)
        },
        'ingredients': [{
            'recipe_id': r['id'],
            'ingredient_id': r['ingredient_id'],
            'ingredient_name': r['ingredient_name'],
            'unit': r['unit'],
            'quantity_required': float(r['quantity_required']),
            'cost_per_unit': float(r['cost_per_unit']),
            'line_cost': round(float(r['line_cost'] or 0), 2)
        } for r in rows],
        'total_recipe_cost': round(total_cost, 2),
        'has_recipe': len(rows) > 0
    })


@foodcost_bp.route('/recipes/<int:menu_item_id>', methods=['POST'])
@token_required
def add_recipe_ingredient(menu_item_id):
    """Add ingredient to recipe."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    # Verify menu item ownership
    item = execute_one(
        "SELECT id FROM menu_items WHERE id = %s AND kitchen_id = %s",
        (menu_item_id, kitchen_id)
    )
    if not item:
        return jsonify({'error': 'Menu item not found'}), 404

    data = request.get_json() or {}
    ingredient_id = data.get('ingredient_id')
    quantity = data.get('quantity_required')

    if not ingredient_id or not quantity:
        return jsonify({'error': 'ingredient_id and quantity_required required'}), 400

    # Verify ingredient belongs to kitchen
    ing = execute_one(
        "SELECT id FROM ingredients WHERE id = %s AND kitchen_id = %s",
        (ingredient_id, kitchen_id)
    )
    if not ing:
        return jsonify({'error': 'Ingredient not found'}), 404

    # Check duplicate
    existing = execute_one(
        "SELECT id FROM recipes WHERE menu_item_id = %s AND ingredient_id = %s",
        (menu_item_id, ingredient_id)
    )
    if existing:
        return jsonify({'error': 'Ingredient already in recipe'}), 409

    result = execute_one("""
        INSERT INTO recipes (menu_item_id, ingredient_id, quantity_required)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (menu_item_id, ingredient_id, float(quantity)))

    return jsonify({
        'message': 'Ingredient added to recipe',
        'id': result['id']
    }), 201


@foodcost_bp.route('/recipes/<int:recipe_id>', methods=['DELETE'])
@token_required
def remove_recipe_ingredient(recipe_id):
    """Remove ingredient from recipe."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    # Verify ownership via join
    r = execute_one("""
        SELECT r.id FROM recipes r
        JOIN menu_items mi ON mi.id = r.menu_item_id
        WHERE r.id = %s AND mi.kitchen_id = %s
    """, (recipe_id, kitchen_id))

    if not r:
        return jsonify({'error': 'Recipe ingredient not found'}), 404

    execute_query(
        "DELETE FROM recipes WHERE id = %s",
        (recipe_id,),
        fetch=False
    )

    return jsonify({'message': 'Removed from recipe'})


@foodcost_bp.route('/recipes/<int:recipe_id>', methods=['PUT'])
@token_required
def update_recipe_quantity(recipe_id):
    """Update quantity in recipe."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    r = execute_one("""
        SELECT r.id FROM recipes r
        JOIN menu_items mi ON mi.id = r.menu_item_id
        WHERE r.id = %s AND mi.kitchen_id = %s
    """, (recipe_id, kitchen_id))

    if not r:
        return jsonify({'error': 'Recipe ingredient not found'}), 404

    data = request.get_json() or {}
    qty = data.get('quantity_required')
    if not qty:
        return jsonify({'error': 'quantity_required required'}), 400

    execute_query("""
        UPDATE recipes SET quantity_required = %s WHERE id = %s
    """, (float(qty), recipe_id), fetch=False)

    return jsonify({'message': 'Quantity updated'})


# ==========================================
# ENDPOINT 3: True Profitability (with recipe cost)
# ==========================================
@foodcost_bp.route('/true-profitability', methods=['GET'])
@token_required
def true_profitability():
    """
    Item profitability using ACTUAL recipe costs (vs estimated cost_price).
    Only includes items that have recipes defined.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = request.args.get('days', '30')
    date_sql = ""
    date_params = []
    if days != 'all':
        try:
            d = int(days)
            date_sql = "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'"
            date_params = [d]
        except (ValueError, TypeError):
            pass

    sql = f"""
        WITH recipe_costs AS (
            SELECT
                r.menu_item_id,
                SUM(r.quantity_required * i.cost_per_unit) AS recipe_cost
            FROM recipes r
            JOIN ingredients i ON i.id = r.ingredient_id
            GROUP BY r.menu_item_id
        )
        SELECT
            mi.id,
            mi.name,
            mi.cost_price AS estimated_cost,
            rc.recipe_cost AS actual_cost,
            mi.selling_price,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue
        FROM menu_items mi
        JOIN recipe_costs rc ON rc.menu_item_id = mi.id
        LEFT JOIN order_items oi ON oi.menu_item_id = mi.id
        LEFT JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.cost_price, rc.recipe_cost, mi.selling_price
        ORDER BY net_revenue DESC
    """

    params = date_params + [kitchen_id]
    rows = execute_query(sql, params)

    items = []
    for r in rows:
        qty = int(r['quantity_sold'] or 0)
        net_rev = float(r['net_revenue'] or 0)
        actual_cost = float(r['actual_cost'] or 0)
        est_cost = float(r['estimated_cost'] or 0)
        selling = float(r['selling_price'] or 0)

        total_actual = actual_cost * qty
        total_est = est_cost * qty

        true_profit = net_rev - total_actual
        est_profit = net_rev - total_est

        true_margin = (true_profit / net_rev * 100) if net_rev > 0 else 0
        food_cost_pct = (total_actual / net_rev * 100) if net_rev > 0 else 0

        items.append({
            'id': r['id'],
            'name': r['name'],
            'selling_price': round(selling, 2),
            'estimated_cost': round(est_cost, 2),
            'actual_cost': round(actual_cost, 2),
            'cost_variance': round(actual_cost - est_cost, 2),
            'quantity_sold': qty,
            'net_revenue': round(net_rev, 2),
            'total_actual_cost': round(total_actual, 2),
            'total_estimated_cost': round(total_est, 2),
            'true_profit': round(true_profit, 2),
            'estimated_profit': round(est_profit, 2),
            'true_margin': round(true_margin, 1),
            'food_cost_pct': round(food_cost_pct, 1)
        })

    return jsonify(items)


# ==========================================
# ENDPOINT 4: Stock Alerts
# ==========================================
@foodcost_bp.route('/stock-alerts', methods=['GET'])
@token_required
def stock_alerts():
    """Ingredients below reorder threshold."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query("""
        SELECT id, name, unit, current_stock, reorder_threshold, cost_per_unit
        FROM ingredients
        WHERE kitchen_id = %s
          AND current_stock <= reorder_threshold
        ORDER BY (current_stock - reorder_threshold) ASC
    """, (kitchen_id,))

    return jsonify([{
        'id': r['id'],
        'name': r['name'],
        'unit': r['unit'] or 'kg',
        'current_stock': float(r['current_stock'] or 0),
        'reorder_threshold': float(r['reorder_threshold'] or 0),
        'shortage': round(float(r['reorder_threshold'] or 0) - float(r['current_stock'] or 0), 2),
        'cost_per_unit': float(r['cost_per_unit'] or 0)
    } for r in rows])


# ==========================================
# ENDPOINT 5: Dashboard Summary
# ==========================================
@foodcost_bp.route('/summary', methods=['GET'])
@token_required
def foodcost_summary():
    """Summary KPIs for food cost analysis."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    # Total ingredients
    ing_summary = execute_one("""
        SELECT
            COUNT(*) AS total_ingredients,
            COUNT(*) FILTER (WHERE current_stock <= reorder_threshold) AS low_stock,
            COALESCE(SUM(current_stock * cost_per_unit), 0) AS stock_value
        FROM ingredients
        WHERE kitchen_id = %s
    """, (kitchen_id,))

    # Recipe coverage
    recipe_summary = execute_one("""
        SELECT
            COUNT(DISTINCT mi.id) FILTER (WHERE r.id IS NOT NULL) AS items_with_recipe,
            COUNT(DISTINCT mi.id) AS total_items
        FROM menu_items mi
        LEFT JOIN recipes r ON r.menu_item_id = mi.id
        WHERE mi.kitchen_id = %s AND mi.is_active = TRUE
    """, (kitchen_id,))

    total_items = int(recipe_summary['total_items'] or 0)
    with_recipe = int(recipe_summary['items_with_recipe'] or 0)
    coverage = (with_recipe / total_items * 100) if total_items > 0 else 0

    return jsonify({
        'total_ingredients': int(ing_summary['total_ingredients'] or 0),
        'low_stock_count': int(ing_summary['low_stock'] or 0),
        'stock_value': round(float(ing_summary['stock_value'] or 0), 2),
        'items_with_recipe': with_recipe,
        'total_items': total_items,
        'recipe_coverage': round(coverage, 1)
    })


# ==========================================
# ENDPOINT 6: Items Missing Recipes
# ==========================================
@foodcost_bp.route('/missing-recipes', methods=['GET'])
@token_required
def missing_recipes():
    """Menu items without any recipe defined."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query("""
        SELECT mi.id, mi.name, mi.selling_price, mi.cost_price
        FROM menu_items mi
        WHERE mi.kitchen_id = %s
          AND mi.is_active = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM recipes r WHERE r.menu_item_id = mi.id
          )
        ORDER BY mi.name
    """, (kitchen_id,))

    return jsonify([{
        'id': r['id'],
        'name': r['name'],
        'selling_price': float(r['selling_price'] or 0),
        'estimated_cost': float(r['cost_price'] or 0)
    } for r in rows])