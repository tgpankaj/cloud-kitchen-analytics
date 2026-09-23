"""
KitchenIQ — Auto-Sync Worker

Runs every N minutes and syncs all connected integrations
across all kitchens.

Uses APScheduler (no Redis needed for MVP).
Can later be swapped for RQ/Celery.
"""
import logging
from datetime import datetime, timedelta

from db.connection import execute_query, execute_one
from services.sync_service import SyncService

from services import notification_service as notif


logger = logging.getLogger(__name__)


# ============================================================
# AUTO-SYNC ALL
# ============================================================

def auto_sync_all():
    """
    Find all connected integrations whose last sync is stale,
    and sync them.
    """
    logger.info("[worker] auto_sync_all started")

    # Find integrations that are connected and either:
    # - never synced, OR
    # - last sync > 4 min ago
    integrations = execute_query(
        """
        SELECT
            i.id,
            i.kitchen_id,
            i.platform,
            i.last_sync_at
        FROM integrations i
        WHERE i.status = 'connected'
          AND i.is_active = TRUE
          AND (
              i.last_sync_at IS NULL
              OR i.last_sync_at < NOW() - INTERVAL '4 minutes'
          )
        ORDER BY i.last_sync_at NULLS FIRST
        LIMIT 50
        """
    )

    if not integrations:
        logger.info("[worker] no stale integrations — nothing to sync")
        return {"synced": 0, "failed": 0}

    synced = 0
    failed = 0

    for integ in integrations:
        try:
            _sync_one(integ)
            synced += 1
        except Exception as e:
            logger.error(f"[worker] sync failed for integ {integ['id']}: {e}")
            failed += 1

    logger.info(f"[worker] auto_sync_all done — synced={synced} failed={failed}")
    return {"synced": synced, "failed": failed}


def _sync_one(integ):
    """Sync a single integration row."""
    platform = integ["platform"]
    kitchen_id = integ["kitchen_id"]

    logger.info(f"[worker] syncing kitchen={kitchen_id} platform={platform}")

    # Build mock integration (later: use real provider by platform)
    if platform in ("zomato", "swiggy", "pos", "website"):
        integration = MockIntegration(kitchen_id, platform=platform)
        integration.connect()
    else:
        raise ValueError(f"Unknown platform: {platform}")

    # Compute 'since' = last sync (or 1 day ago)
    since = integ["last_sync_at"] or (datetime.utcnow() - timedelta(days=1))
    # Round down by 1 min for overlap safety
    since = since - timedelta(minutes=1)

    service = SyncService(
        integration_id=integ["id"],
        kitchen_id=kitchen_id,
        platform=platform,
    )

    result = service.run(integration, since=since)
    logger.info(f"[worker] result: {result}")

    # Notify on success or failure
    try:
        if result.get("status") == "success" and result.get("created", 0) > 0:
            notif.notify_sync_success(kitchen_id, platform, result["created"])
        elif result.get("status") == "failed":
            notif.notify_sync_failed(kitchen_id, platform, result.get("error", "Unknown error"))
    except Exception as _e:
        logger.warning(f"[worker] notification failed: {_e}")

    return result


# ============================================================
# SCHEDULER SETUP (called from app.py)
# ============================================================

_scheduler = None


def start_scheduler(app, interval_minutes=5):
    """
    Start the background scheduler inside the Flask app.
    Idempotent — safe to call multiple times.
    """
    global _scheduler

    if _scheduler is not None:
        logger.info("[worker] scheduler already running")
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler(daemon=True)

    def _job():
        """Wrapper to run within Flask app context."""
        with app.app_context():
            try:
                auto_sync_all()
            except Exception as e:
                logger.error(f"[worker] job error: {e}")

    scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="auto_sync_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    _scheduler = scheduler

    logger.info(f"[worker] scheduler started — every {interval_minutes} min")
    return scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[worker] scheduler stopped")
