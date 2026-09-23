"""
Notification Routes
-------------------
In-app notifications for KitchenIQ.
"""
from flask import Blueprint, request, jsonify

from middleware.auth import token_required
from services import notification_service as ns


notifications_bp = Blueprint("notifications_kpi", __name__)


def get_kitchen_id(request):
    kid = request.args.get("kitchen_id")
    if kid:
        try:
            return int(kid)
        except (ValueError, TypeError):
            pass
    from db.connection import execute_one
    row = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    return row["id"] if row else None


# ============================================================
# LIST
# ============================================================

@notifications_bp.route("/", methods=["GET"])
@token_required
def list_all():
    kitchen_id = get_kitchen_id(request)
    limit = min(int(request.args.get("limit", 20)), 100)
    unread_only = request.args.get("unread") == "1"

    items = ns.list_notifications(
        user_id=request.user_id,
        kitchen_id=kitchen_id,
        limit=limit,
        unread_only=unread_only,
    )
    return jsonify(items)


# ============================================================
# UNREAD COUNT (for bell badge)
# ============================================================

@notifications_bp.route("/unread-count", methods=["GET"])
@token_required
def unread():
    kitchen_id = get_kitchen_id(request)
    count = ns.unread_count(request.user_id, kitchen_id)
    return jsonify({"unread": count})


# ============================================================
# MARK READ
# ============================================================

@notifications_bp.route("/<int:nid>/read", methods=["POST"])
@token_required
def mark_one(nid):
    ns.mark_read(request.user_id, nid)
    return jsonify({"ok": True, "id": nid})


@notifications_bp.route("/read-all", methods=["POST"])
@token_required
def mark_all():
    kitchen_id = get_kitchen_id(request)
    ns.mark_all_read(request.user_id, kitchen_id)
    return jsonify({"ok": True})


# ============================================================
# DELETE
# ============================================================

@notifications_bp.route("/<int:nid>", methods=["DELETE"])
@token_required
def delete_one(nid):
    ns.delete_notification(request.user_id, nid)
    return jsonify({"ok": True})


# ============================================================
# TEST (creates a sample notification for the current user)
# ============================================================

@notifications_bp.route("/test", methods=["POST"])
@token_required
def test_create():
    kitchen_id = get_kitchen_id(request)
    ns.create_notification(
        user_id=request.user_id,
        kitchen_id=kitchen_id,
        type="test",
        title="Test notification",
        message="If you see this, notifications are working!",
        severity="info",
    )
    return jsonify({"ok": True})
