import logging
import sys


def configure_logging(environment: str = "development") -> None:
    """
    Set up root logger.
    - production  → JSON lines (machine-readable, one record per line)
    - development → human-readable with timestamps
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any handlers that may already be attached (e.g. from basicConfig calls)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        from pythonjsonlogger import jsonlogger

        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "asyncio", "rq.worker"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
