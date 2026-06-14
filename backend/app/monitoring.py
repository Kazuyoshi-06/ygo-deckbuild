"""
Prometheus metrics and webhook alerting.

Metrics are registered once at module import time.
Call record_sync_result() from sync services after each run.
Call send_alert_webhook() on failure if ALERT_WEBHOOK_URL is configured.
"""
import logging
from datetime import datetime, timezone

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# ── Prometheus metrics ──────────────────────────────────────────────────────

sync_runs_total = Counter(
    "ygo_sync_runs_total",
    "Total number of sync runs",
    ["sync_type", "status"],  # status: success | failed
)

sync_duration_seconds = Histogram(
    "ygo_sync_duration_seconds",
    "Sync job duration in seconds",
    ["sync_type"],
    buckets=[5, 15, 30, 60, 120, 300, 600, 1800, 3600],
)


def record_sync_result(sync_type: str, status: str, elapsed: float) -> None:
    """Record a completed (success or failed) sync run into Prometheus."""
    sync_runs_total.labels(sync_type=sync_type, status=status).inc()
    sync_duration_seconds.labels(sync_type=sync_type).observe(elapsed)


# ── Webhook alerting ────────────────────────────────────────────────────────

async def send_alert_webhook(sync_type: str, error: str, run_id: int) -> None:
    """
    POST an alert to the configured webhook URL on sync failure.
    Works with Slack incoming webhooks, Discord webhooks, and generic HTTP.
    Silently swallows errors — alerting must never break the main flow.
    """
    from app.config import settings  # late import to avoid circular dependency

    url = settings.alert_webhook_url.strip()
    if not url:
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"🚨 YGO Intel — {sync_type} sync FAILED\n"
        f"Run ID: {run_id}\n"
        f"Error: {error}\n"
        f"Time: {ts}"
    )

    # Send keys for both Slack (`text`) and Discord (`content`) formats
    payload: dict = {"text": text, "content": text}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "Alert webhook returned %s for %s sync failure",
                    resp.status_code,
                    sync_type,
                )
    except Exception as exc:
        logger.warning("Alert webhook delivery failed: %s", exc)
