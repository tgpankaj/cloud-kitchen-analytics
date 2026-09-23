"""
Integration Routes
------------------
Manage platform integrations (Zomato, Swiggy, POS, Mock).
"""
from flask import Blueprint, request, jsonify

from middleware.auth import token_required
from db.connection import execute_query, execute_one
from services.sync_service import SyncService
from services.integrations.mock import MockIntegration


integrations_bp = Blueprint("integrations", __name__)


# ========================================================
# HELPERS
# ========================================================

def get_kitchen_id(request):
    kitchen_id = request.args.get("kitchen_id")
    if kitchen_id:
        try:
            return int(kitchen_id)
        except (ValueError, TypeError):
            pass

    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    return kitchen["id"] if kitchen else None


def get_integration(integration_id, kitchen_id):
    """Fetch integration with ownership check."""
    return execute_one(
        """
        SELECT id, kitchen_id, platform, status, auth_type,
               last_sync_at, last_successful_sync, last_error,
               created_at, updated_at
        FROM integrations
        WHERE id = %s AND kitchen_id = %s
        """,
        (integration_id, kitchen_id)
    )


# ========================================================
# LIST INTEGRATIONS
# GET /api/integrations
# ========================================================

@integrations_bp.route("/", methods=["GET"])
@token_required
def list_integrations():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    rows = execute_query(
        """
        SELECT id, platform, status, auth_type,
               last_sync_at, last_successful_sync, last_error,
               created_at
        FROM integrations
        WHERE kitchen_id = %s
        ORDER BY platform
        """,
        (kitchen_id,)
    )

    return jsonify([
        {
            "id": r["id"],
            "platform": r["platform"],
            "status": r["status"],
            "auth_type": r["auth_type"],
            "last_sync_at": str(r["last_sync_at"]) if r["last_sync_at"] else None,
            "last_successful_sync": str(r["last_successful_sync"]) if r["last_successful_sync"] else None,
            "last_error": r["last_error"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ])


# ========================================================
# CONNECT
# POST /api/integrations/connect
# Body: { "platform": "zomato" }
# ========================================================

@integrations_bp.route("/connect", methods=["POST"])
@token_required
def connect():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    data = request.get_json() or {}
    platform = (data.get("platform") or "").lower().strip()

    if platform not in ("zomato", "swiggy", "pos", "website"):
        return jsonify({"error": f"Unsupported platform: {platform}"}), 400

    # Check if already exists
    existing = execute_one(
        "SELECT id, status FROM integrations WHERE kitchen_id = %s AND platform = %s",
        (kitchen_id, platform)
    )

    if existing and existing["status"] == "connected":
        return jsonify({"message": "Already connected", "id": existing["id"]}), 200

    # Create MockIntegration for now
    integration = MockIntegration(kitchen_id, platform=platform)
    result = integration.connect()

    if existing:
        # Update
        execute_query(
            """
            UPDATE integrations
            SET status = 'connected',
                auth_type = %s,
                credentials_encrypted = %s,
                access_token_encrypted = %s,
                token_expires_at = %s,
                last_error = NULL,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                result.get("auth_type", "mock"),
                None,
                result.get("access_token"),
                result.get("token_expires_at"),
                existing["id"],
            ),
            fetch=False
        )
        integration_id = existing["id"]
    else:
        row = execute_one(
            """
            INSERT INTO integrations
                (kitchen_id, platform, status, auth_type,
                 access_token_encrypted, token_expires_at)
            VALUES (%s, %s, 'connected', %s, %s, %s)
            RETURNING id
            """,
            (
                kitchen_id,
                platform,
                result.get("auth_type", "mock"),
                result.get("access_token"),
                result.get("token_expires_at"),
            )
        )
        integration_id = row["id"]

    return jsonify({
        "message": f"{platform.capitalize()} connected successfully",
        "id": integration_id,
        "platform": platform,
        "status": "connected",
    }), 201


# ========================================================
# DISCONNECT
# POST /api/integrations/disconnect
# Body: { "platform": "zomato" }
# ========================================================

@integrations_bp.route("/disconnect", methods=["POST"])
@token_required
def disconnect():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    data = request.get_json() or {}
    platform = (data.get("platform") or "").lower().strip()

    existing = execute_one(
        "SELECT id FROM integrations WHERE kitchen_id = %s AND platform = %s",
        (kitchen_id, platform)
    )
    if not existing:
        return jsonify({"error": "Integration not found"}), 404

    execute_query(
        """
        UPDATE integrations
        SET status = 'disconnected',
            access_token_encrypted = NULL,
            refresh_token_encrypted = NULL,
            token_expires_at = NULL,
            updated_at = NOW()
        WHERE id = %s
        """,
        (existing["id"],),
        fetch=False
    )

    return jsonify({
        "message": f"{platform.capitalize()} disconnected",
        "platform": platform,
        "status": "disconnected",
    })


# ========================================================
# TEST CONNECTION
# POST /api/integrations/test
# ========================================================

@integrations_bp.route("/test", methods=["POST"])
@token_required
def test_connection():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    data = request.get_json() or {}
    platform = (data.get("platform") or "").lower().strip()

    integration = MockIntegration(kitchen_id, platform=platform)
    integration.connect()

    return jsonify({
        "platform": platform,
        "connected": integration.test_connection(),
    })


# ========================================================
# SYNC
# POST /api/integrations/sync
# Body: { "platform": "zomato" }
# ========================================================

@integrations_bp.route("/sync", methods=["POST"])
@token_required
def sync():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    data = request.get_json() or {}
    platform = (data.get("platform") or "").lower().strip()

    # Must be connected
    integration_row = execute_one(
        """
        SELECT id, status FROM integrations
        WHERE kitchen_id = %s AND platform = %s
        """,
        (kitchen_id, platform)
    )

    if not integration_row:
        return jsonify({
            "error": f"{platform.capitalize()} not connected",
            "hint": "Call /api/integrations/connect first"
        }), 400

    if integration_row["status"] != "connected":
        return jsonify({
            "error": f"{platform.capitalize()} is {integration_row['status']}"
        }), 400

    # Run sync
    integration = MockIntegration(kitchen_id, platform=platform)
    integration.connect()

    service = SyncService(
        integration_id=integration_row["id"],
        kitchen_id=kitchen_id,
        platform=platform,
    )

    # Sync last 7 days on first run, else last 1 day
    since = None  # Mock will handle default

    result = service.run(integration, since=since)

    return jsonify({
        "platform": platform,
        "status": result["status"],
        "fetched": result.get("fetched", 0),
        "created": result.get("created", 0),
        "updated": result.get("updated", 0),
        "failed": result.get("failed", 0),
        "duration": round(result.get("duration", 0), 2),
    })


# ========================================================
# GET ONE INTEGRATION
# GET /api/integrations/<id>
# ========================================================

@integrations_bp.route("/<int:integration_id>", methods=["GET"])
@token_required
def get_one(integration_id):
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    row = get_integration(integration_id, kitchen_id)
    if not row:
        return jsonify({"error": "Integration not found"}), 404

    return jsonify({
        "id": row["id"],
        "platform": row["platform"],
        "status": row["status"],
        "last_sync_at": str(row["last_sync_at"]) if row["last_sync_at"] else None,
        "last_successful_sync": str(row["last_successful_sync"]) if row["last_successful_sync"] else None,
        "last_error": row["last_error"],
    })


# ========================================================
# GET SYNC LOGS
# GET /api/integrations/<id>/logs
# ========================================================

@integrations_bp.route("/<int:integration_id>/logs", methods=["GET"])
@token_required
def logs(integration_id):
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({"error": "No kitchen found"}), 404

    integration = get_integration(integration_id, kitchen_id)
    if not integration:
        return jsonify({"error": "Integration not found"}), 404

    limit = min(int(request.args.get("limit", 20)), 100)

    rows = execute_query(
        """
        SELECT id, status, started_at, completed_at,
               records_fetched, records_created, records_updated,
               records_failed, error_message, duration_seconds
        FROM sync_logs
        WHERE integration_id = %s
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (integration_id, limit)
    )

    return jsonify([
        {
            "id": r["id"],
            "status": r["status"],
            "started_at": str(r["started_at"]) if r["started_at"] else None,
            "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            "fetched": r["records_fetched"],
            "created": r["records_created"],
            "updated": r["records_updated"],
            "failed": r["records_failed"],
            "error": r["error_message"],
            "duration": float(r["duration_seconds"]) if r["duration_seconds"] else None,
        }
        for r in rows
    ])


# ========================================================
# HEALTH
# GET /api/integrations/
# ========================================================

@integrations_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "KitchenIQ Integrations",
        "status": "ok",
        "endpoints": [
            "GET  /api/integrations/",
            "POST /api/integrations/connect",
            "POST /api/integrations/disconnect",
            "POST /api/integrations/test",
            "POST /api/integrations/sync",
            "GET  /api/integrations/<id>",
            "GET  /api/integrations/<id>/logs",
        ]
    })


# ========================================================
# MANUAL TRIGGER (Testing only)
# POST /api/integrations/worker/run-now
# ========================================================

@integrations_bp.route("/worker/run-now", methods=["POST"])
@token_required
def worker_run_now():
    """Trigger the auto-sync worker immediately. Testing only."""
    from workers.sync_worker import auto_sync_all
    try:
        result = auto_sync_all()
        return jsonify({
            "message": "Worker ran",
            "synced": result.get("synced", 0),
            "failed": result.get("failed", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
