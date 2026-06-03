"""
src/utils/logger.py — Centralized logging configuration for Finnie.

Two output formats, controlled by the LOG_FORMAT env var:
  - LOG_FORMAT=human (default) — pipe-delimited, easy to scan in a terminal
  - LOG_FORMAT=json             — JSON-per-line, machine-parsable for log aggregators

Every log record is automatically tagged with the current LangSmith trace_id
(when a LangChain/LangGraph call is in progress). This lets us jump from a log
line to its full LangSmith trace tree with one click in production tooling.
"""

import logging
import os
import sys

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None  # JSON format requires python-json-logger; falls back to human


# Format strings
LOG_FORMAT_HUMAN = "%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


class TraceIdFilter(logging.Filter):
    """Inject the current LangSmith trace_id into every log record.

    Returns True unconditionally (i.e., filter never drops records — it only
    enriches them with the `trace_id` attribute).

    LangSmith exposes the active run tree only while a LangChain/LangGraph
    call is in progress. Outside of an LLM call (e.g., logging from a UI
    helper), there is no active run and trace_id is None.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from langsmith.run_helpers import get_current_run_tree

            run = get_current_run_tree()
            record.trace_id = str(run.id) if run else None
        except Exception:
            # Defensive: never let logging itself fail because of langsmith
            record.trace_id = None
        return True


def _build_human_formatter() -> logging.Formatter:
    return logging.Formatter(LOG_FORMAT_HUMAN, datefmt=DATE_FORMAT)


def _build_json_formatter() -> logging.Formatter:
    """Build a JSON formatter; fall back to human format if package missing."""
    if jsonlogger is None:
        return _build_human_formatter()

    # Fields to emit. Order doesn't matter in JSON, but list them explicitly
    # so we know exactly what's in production logs.
    fields = "%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s"
    return jsonlogger.JsonFormatter(
        fields,
        rename_fields={
            "asctime": "timestamp",
            "name": "logger",
            "levelname": "level",
        },
    )


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a named logger with a consistent format + trace-id enrichment.

    Idempotent: safe to call from the same module multiple times.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        log_format = os.getenv("LOG_FORMAT", "human").lower()
        if log_format == "json":
            formatter = _build_json_formatter()
        else:
            formatter = _build_human_formatter()

        handler.setFormatter(formatter)
        handler.addFilter(TraceIdFilter())   # enriches every record with trace_id
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False                  # prevent duplicate logs from root logger
    return logger