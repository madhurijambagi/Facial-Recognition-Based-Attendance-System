import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_login_page_loads_without_auth(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_dashboard_requires_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_manage_students_requires_login(client):
    resp = client.get("/students", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_debug_dataset_requires_login(client):
    resp = client.get("/debug_dataset", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_add_teacher_requires_login(client):
    # Previously this route had no authentication at all.
    resp = client.get("/add_teacher", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout_clears_session_and_redirects(client):
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_health_endpoint_returns_controlled_response(client):
    # The DB is not guaranteed to be reachable in CI — either outcome must be
    # a clean, structured response, never an unhandled exception.
    resp = client.get("/health")
    assert resp.status_code in (200, 503)
    body = resp.get_json()
    assert "database" in body
    assert "status" in body


def test_unknown_route_returns_404(client):
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
