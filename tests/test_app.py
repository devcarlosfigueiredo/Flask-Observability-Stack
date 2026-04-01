"""
Tests for the Flask observability application.
Validates endpoints, health checks, and metrics exposure.
"""

import pytest
import json

# Ensure the app module is importable
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ─── Health & Ready ───────────────────────────────────────────────────────────

def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client):
    response = client.get("/health")
    data = json.loads(response.data)
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_ready_returns_200_or_503(client):
    response = client.get("/ready")
    assert response.status_code in (200, 503)


def test_ready_response_has_checks(client):
    response = client.get("/ready")
    data = json.loads(response.data)
    assert "checks" in data
    assert "database" in data["checks"]
    assert "cache" in data["checks"]


# ─── API Endpoints ────────────────────────────────────────────────────────────

def test_products_returns_200(client):
    response = client.get("/api/products")
    assert response.status_code == 200


def test_products_returns_items(client):
    response = client.get("/api/products")
    data = json.loads(response.data)
    assert "items" in data
    assert len(data["items"]) > 0
    assert "total" in data


def test_orders_returns_200(client):
    response = client.get("/api/orders")
    assert response.status_code == 200


def test_orders_response_structure(client):
    response = client.get("/api/orders")
    data = json.loads(response.data)
    assert "orders" in data
    for order in data["orders"]:
        assert "id" in order
        assert "status" in order


def test_process_returns_200_or_500(client):
    """Process endpoint has ~10% error rate."""
    response = client.post("/api/process")
    assert response.status_code in (200, 500)


def test_force_error_returns_500(client):
    response = client.get("/api/error")
    assert response.status_code == 500


# ─── Metrics Endpoint ─────────────────────────────────────────────────────────

def test_metrics_endpoint_returns_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type(client):
    response = client.get("/metrics")
    assert "text/plain" in response.content_type


def test_metrics_contains_http_requests_total(client):
    # Make a request first so the metric exists
    client.get("/health")
    response = client.get("/metrics")
    assert b"http_requests_total" in response.data


def test_metrics_contains_latency_histogram(client):
    client.get("/health")
    response = client.get("/metrics")
    assert b"http_request_duration_seconds" in response.data


def test_metrics_contains_active_requests_gauge(client):
    response = client.get("/metrics")
    assert b"http_active_requests" in response.data


def test_metrics_contains_error_counter(client):
    client.get("/api/error")
    response = client.get("/metrics")
    assert b"http_errors_total" in response.data
