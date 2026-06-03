"""
src/utils/logger.py — Centralized logging configuration for Finnie.

Two output formats, controlled by the LOG_FORMAT env var:
  - LOG_FORMAT=human (default): pipe-delimited + inline extras for terminal dev
  - LOG_FORMAT=json            : one JSON object per line for log aggregators

In BOTH modes, log calls use `logger.info("msg", extra={"agent": "qa", ...})`.
Human mode appends extras to the line; JSON mode merges them into the object.
This means the same code reads in dev AND parses perfectly in prod.

Every log record is also tagged with the current LangSmith trace_id when
a LangChain/LangGraph call is in progress (via TraceIdFilter).
"""

import logging
import os
import sys

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


LOG_FORMAT_HUMAN = "%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


# ──────────────────────────────────────────────────────────────────────────────
# Custom human formatter: pipe-delimited base + inline extras
# ──────────────────────────────────────────────────────────────────────────────
class HumanFormatter(logging.Formatter):
    """Standard pipe format PLUS inline `extra={...}` fields appended.

    A call like
        logger.info("News agent: invoking LLM", extra={"history_len": 0, "loop_cnt": 0})
    produces
        15:16:19 | finnie.agents.news.agent | INFO | News agent: invoking LLM | history_len=0 loop_cnt=0

    Filters out built-in LogRecord attributes so only YOUR extras appear.
    """

    # Built-in LogRecord attributes — any record attribute NOT in this set
    # came from `extra={...}` and should be displayed inline.
    _STANDARD_ATTRS = frozenset({
        "name", "msg", "args", "levelname", "levelno",
        "pathname", "filename", "module", "exc_info", "exc_text",
        "stack_info", "lineno", "funcName", "created", "msecs",
        "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime",
        "trace_id",     # exclude — UUID is too noisy for terminal display
        "taskName",     # Python 3.12+ adds this
    })

    def format(self, record: logging.LogRecord) -> str:
        # Render the standard pipe-delimited base
        base = super().format(record)

        # Collect anything passed via extra={...}
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in self._STANDARD_ATTRS
        }

        if not extras:
            return base

        # Append inline: " | key1=value1 key2=value2"
        extras_str = " ".join(f"{k}={v}" for k, v in extras.items())
        return f"{base} | {extras_str}"


class TraceIdFilter(logging.Filter):
    """Inject the current LangSmith trace_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from langsmith.run_helpers import get_current_run_tree
            run = get_current_run_tree()
            record.trace_id = str(run.id) if run else None
        except Exception:
            record.trace_id = None
        return True


def _build_human_formatter() -> logging.Formatter:
    return HumanFormatter(LOG_FORMAT_HUMAN, datefmt=DATE_FORMAT)


def _build_json_formatter() -> logging.Formatter:
    if jsonlogger is None:
        return _build_human_formatter()

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
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        log_format = os.getenv("LOG_FORMAT", "human").lower()
        formatter = _build_json_formatter() if log_format == "json" else _build_human_formatter()

        handler.setFormatter(formatter)
        handler.addFilter(TraceIdFilter())
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False
    return logger