"""
src/api/rate_limit.py — slowapi Limiter, kept in its own module.

Why a separate module: both main.py and routes/*.py need to reference
the same Limiter instance (main.py attaches it to app.state, routes use
the @limiter.limit decorator). Having it in main.py would create a
circular import (main imports routes; routes would import main).

Single-source-of-truth pattern: define once, import from anywhere.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP rate limiter. Bot defense even before the cost circuit breaker.
# When deployed behind ALB, get_remote_address honors X-Forwarded-For so
# we see the real client IP, not the ALB's internal IP.
limiter = Limiter(key_func=get_remote_address)
