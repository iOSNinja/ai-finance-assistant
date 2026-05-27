"""
logger.py — Centralized logging configuration for Finnie.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a named logger with a consistent stream handler."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger
