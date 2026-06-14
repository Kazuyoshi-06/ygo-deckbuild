#!/usr/bin/env python
"""
Start the RQ worker for YGO Intel background sync jobs.

Run from the backend/ directory:
    python start_worker.py

The worker consumes the "ygo" queue and executes sync jobs
(card catalog sync, banlist sync, CDB sync) in a separate process,
so jobs persist even if the API server restarts.

Requirements: Redis must be running at the URL set in .env (REDIS_URL).
"""
from redis import Redis
from rq import Worker

from app.config import settings
from app.logging_config import configure_logging

configure_logging(settings.environment)

if __name__ == "__main__":
    redis = Redis.from_url(settings.redis_url)
    worker = Worker(["ygo"], connection=redis)
    import logging
    logging.getLogger(__name__).info(
        "YGO Intel worker started — listening on queue 'ygo' at %s",
        settings.redis_url,
    )
    worker.work(with_scheduler=True)
