from fastapi.testclient import TestClient

from api.index import app


def test_login_works_on_cold_start_without_lifespan():
    # No `with TestClient(app)`: lifespan never runs, as can happen on serverless hosts.
    client = TestClient(app)
    admin = client.post("/api/admin/login", json={"email": "admin@test.local", "password": "admin-pass-1"})
    assert admin.status_code == 200, admin.text
    demo = client.post("/api/auth/login", json={"email": "cliente@prueba.com", "password": "cliente1234"})
    assert demo.status_code == 200, demo.text
