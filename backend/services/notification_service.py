"""
NotificationService — create and manage in-app notifications.
"""
from db.connection import execute_query, execute_one


# ============================================================
# CREATE
# ============================================================

def create_notification(
    user_id,
    kitchen_id,
    type,
    title,
    message=None,
    severity="info",
    link=None,
    metadata=None,
):
    """
    Create a notification. Safe to call from anywhere (worker, routes).
    Returns the new notification ID or None on failure.
    """
    try:
        row = execute_one(
            """
            INSERT INTO notifications
                (user_id, kitchen_id, type, severity, title, message, link, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                kitchen_id,
                type,
                severity,
                title,
                message,
                link,
                metadata,
            )
        )
        return row["id"] if row else None
    except Exception as e:
        print(f"[notif] create failed: {e}")
        return None


def notify_kitchen_owner(kitchen_id, type, title, message=None,
                         severity="info", link=None, metadata=None):
    """
    Convenience: find kitchen owner's user_id, then notify them.
    """
    kitchen = execute_one(
        "SELECT user_id FROM kitchens WHERE id = %s",
        (kitchen_id,)
    )
    if not kitchen:
        return None
    return create_notification(
        user_id=kitchen["user_id"],
        kitchen_id=kitchen_id,
        type=type,
        title=title,
        message=message,
        severity=severity,
        link=link,
        metadata=metadata,
    )


# ============================================================
# LIST / READ
# ============================================================

def list_notifications(user_id, kitchen_id=None, limit=20, unread_only=False):
    """List notifications for a user (optionally for a specific kitchen)."""
    where = ["user_id = %s"]
    params = [user_id]

    if kitchen_id:
        where.append("kitchen_id = %s")
        params.append(kitchen_id)

    if unread_only:
        where.append("is_read = FALSE")

    sql = f"""
        SELECT id, kitchen_id, type, severity, title, message, link,
               metadata, is_read, created_at
        FROM notifications
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT %s
    """
    params.append(limit)

    rows = execute_query(sql, tuple(params))
    return [
        {
            "id": r["id"],
            "kitchen_id": r["kitchen_id"],
            "type": r["type"],
            "severity": r["severity"],
            "title": r["title"],
            "message": r["message"],
            "link": r["link"],
            "metadata": r["metadata"],
            "is_read": bool(r["is_read"]),
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ]


def unread_count(user_id, kitchen_id=None):
    where = ["user_id = %s", "is_read = FALSE"]
    params = [user_id]
    if kitchen_id:
        where.append("kitchen_id = %s")
        params.append(kitchen_id)

    row = execute_one(
        f"SELECT COUNT(*)::int AS c FROM notifications WHERE {' AND '.join(where)}",
        tuple(params)
    )
    return row["c"] if row else 0


def mark_read(user_id, notification_id):
    return execute_query(
        "UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s",
        (notification_id, user_id),
        fetch=False
    )


def mark_all_read(user_id, kitchen_id=None):
    if kitchen_id:
        return execute_query(
            "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND kitchen_id = %s AND is_read = FALSE",
            (user_id, kitchen_id),
            fetch=False
        )
    return execute_query(
        "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
        (user_id,),
        fetch=False
    )


def delete_notification(user_id, notification_id):
    return execute_query(
        "DELETE FROM notifications WHERE id = %s AND user_id = %s",
        (notification_id, user_id),
        fetch=False
    )


# ============================================================
# EVENT HELPERS (called by workers/services)
# ============================================================

def notify_sync_failed(kitchen_id, platform, error):
    return notify_kitchen_owner(
        kitchen_id,
        type="sync_failed",
        title=f"{platform.capitalize()} sync failed",
        message=str(error)[:500],
        severity="danger",
        link=f"/dashboard-pro.html",
        metadata={"platform": platform},
    )


def notify_sync_success(kitchen_id, platform, created):
    if created <= 0:
        return None
    return notify_kitchen_owner(
        kitchen_id,
        type="sync_success",
        title=f"{created} new order{'s' if created > 1 else ''} from {platform.capitalize()}",
        message="Dashboard updated with latest data.",
        severity="success",
        link="/dashboard-pro.html",
        metadata={"platform": platform, "created": created},
    )


def notify_insight_danger(kitchen_id, title, message):
    return notify_kitchen_owner(
        kitchen_id,
        type="insight_alert",
        title=title,
        message=message,
        severity="warning",
        link="/insights.html",
        metadata={},
    )
