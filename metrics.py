"""
Prometheus metrics definitions for the Flask application.
All metrics follow the RED method: Rate, Errors, Duration.
"""

import functools
import time

from prometheus_client import Counter, Histogram, Gauge, Info

# ─── Application Info ─────────────────────────────────────────────────────────
APP_INFO = Info(
    "flask_app",
    "Flask application metadata",
)
APP_INFO.info({
    "version": "1.0.0",
    "framework": "flask",
    "language": "python",
})

# ─── RED Metrics ──────────────────────────────────────────────────────────────

# Rate — total requests
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

# Duration — request latency histogram
# Buckets tuned for a web API: SLO target p99 < 500ms
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5],
)

# Errors — explicit error counter with error type label
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    labelnames=["endpoint", "error_type"],
)

# ─── Saturation ───────────────────────────────────────────────────────────────

# Active in-flight requests (gauge — can go up and down)
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of currently active HTTP requests",
)

# ─── Business Metrics (SLI-aligned) ──────────────────────────────────────────

ORDERS_PROCESSED = Counter(
    "orders_processed_total",
    "Total orders successfully processed",
)

PRODUCTS_LISTED = Counter(
    "products_listed_total",
    "Total product listing requests served",
)


# ─── Decorator ────────────────────────────────────────────────────────────────
def track_request(endpoint_name: str):
    """
    Decorator to increment domain-specific counters per endpoint.
    Use in addition to the global middleware for fine-grained tracking.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            # Increment domain counters based on endpoint
            if endpoint_name == "orders":
                ORDERS_PROCESSED.inc()
            elif endpoint_name == "products":
                PRODUCTS_LISTED.inc()
            return result
        return wrapper
    return decorator
