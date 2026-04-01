"""
Flask Application with full observability instrumentation.
Exposes /health, /metrics, and simulated endpoints with variable latency.
"""

import logging
import os
import random
import time

from flask import Flask, jsonify, request

from metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    ERROR_COUNT,
    track_request,
)

# ─── Structured logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)
logger = logging.getLogger("flask-app")

# ─── App factory ──────────────────────────────────────────────────────────────
app = Flask(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


# ─── Middleware: record every request ─────────────────────────────────────────
@app.before_request
def before_request():
    request.start_time = time.time()
    ACTIVE_REQUESTS.inc()


@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    endpoint = request.endpoint or "unknown"
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    ACTIVE_REQUESTS.dec()

    logger.info(
        "request completed",
        extra={
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "latency_ms": round(latency * 1000, 2),
            "environment": ENVIRONMENT,
        },
    )
    return response


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    """Liveness & readiness probe."""
    return jsonify(
        status="healthy",
        version=APP_VERSION,
        environment=ENVIRONMENT,
        timestamp=time.time(),
    )


@app.route("/ready")
def ready():
    """Readiness probe — simulates dependency checks."""
    checks = {
        "database": _check_database(),
        "cache": _check_cache(),
    }
    all_ok = all(v["ok"] for v in checks.values())
    status_code = 200 if all_ok else 503

    if not all_ok:
        logger.warning("readiness check failed: %s", checks)

    return jsonify(status="ready" if all_ok else "degraded", checks=checks), status_code


@app.route("/api/products")
@track_request("products")
def products():
    """Simulates a product listing with variable latency (fast path)."""
    _simulate_latency(min_ms=10, max_ms=80)
    items = [{"id": i, "name": f"Product {i}", "price": round(random.uniform(5, 500), 2)} for i in range(1, 11)]
    logger.info("products endpoint called, returning %d items", len(items))
    return jsonify(items=items, total=len(items))


@app.route("/api/orders")
@track_request("orders")
def orders():
    """Simulates an orders endpoint with occasionally high latency."""
    _simulate_latency(min_ms=50, max_ms=600)  # occasionally > 500ms → triggers alert
    orders_data = [{"id": i, "status": random.choice(["pending", "shipped", "delivered"])} for i in range(1, 6)]
    logger.info("orders endpoint called")
    return jsonify(orders=orders_data)


@app.route("/api/process", methods=["POST"])
@track_request("process")
def process():
    """Simulates a heavy processing endpoint with occasional errors."""
    _simulate_latency(min_ms=100, max_ms=900)

    # ~10% chance of error — keeps error_rate SLO interesting
    if random.random() < 0.10:
        ERROR_COUNT.labels(endpoint="process", error_type="processing_error").inc()
        logger.error("processing failed: simulated internal error")
        return jsonify(error="Processing failed", code="PROC_ERR_001"), 500

    logger.info("processing completed successfully")
    return jsonify(status="processed", job_id=f"job-{random.randint(10000, 99999)}")


@app.route("/api/slow")
@track_request("slow")
def slow():
    """Always slow endpoint — useful for latency alert testing."""
    _simulate_latency(min_ms=600, max_ms=1200)
    logger.warning("slow endpoint called — this always triggers the latency alert")
    return jsonify(status="done", message="This endpoint is intentionally slow")


@app.route("/api/error")
def force_error():
    """Forces a 500 — useful for testing error alerts."""
    ERROR_COUNT.labels(endpoint="error", error_type="forced_error").inc()
    logger.error("forced error endpoint called")
    return jsonify(error="Forced error for testing"), 500


@app.route("/metrics")
def metrics_endpoint():
    """Prometheus metrics — scraped every 15s."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _simulate_latency(min_ms: int, max_ms: int):
    """Simulates realistic, non-uniform latency."""
    delay = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay)


def _check_database() -> dict:
    """Simulates a DB connectivity check (always ok in this demo)."""
    return {"ok": True, "latency_ms": round(random.uniform(1, 5), 2)}


def _check_cache() -> dict:
    """Simulates a cache check — 95% uptime."""
    ok = random.random() > 0.05
    return {"ok": ok, "latency_ms": round(random.uniform(0.5, 2), 2) if ok else None}


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info("Starting Flask app on port %d (env: %s, version: %s)", port, ENVIRONMENT, APP_VERSION)
    app.run(host="0.0.0.0", port=port, debug=False)
