import pytest
from fastapi.testclient import TestClient

from api.index import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan -> creates tables and seeds data
        yield c


def auth(client, email, password="password123", name="Ana Perez"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def admin_headers(client):
    r = client.post("/api/admin/login", json={"email": "admin@test.local", "password": "admin-pass-1"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_register_login_and_duplicate(client):
    auth(client, "ana@example.com")
    assert client.post("/api/auth/register", json={"name": "Ana", "email": "ANA@example.com",
                                                   "password": "password123"}).status_code == 409
    ok = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "password123"})
    assert ok.status_code == 200
    bad = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401


def test_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={"name": "Bo", "email": "bo@example.com", "password": "123"})
    assert r.status_code == 422


def test_checkout_requires_login(client):
    assert client.post("/api/orders", json={"lines": [{"product_id": 1, "quantity": 1}]}).status_code == 401


def test_purchase_updates_stock_and_history(client):
    h = auth(client, "buyer@example.com", name="Comprador")
    before = {p["id"]: p for p in client.get("/api/products").json()}
    r = client.post("/api/orders", headers=h, json={"lines": [
        {"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 3}]})
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["subtotal"] == "36.25" and order["tax"] == "7.61" and order["total"] == "43.86"
    after = {p["id"]: p for p in client.get("/api/products").json()}
    assert after[1]["stock"] == before[1]["stock"] - 2
    assert len(client.get("/api/orders", headers=h).json()) == 1


def test_insufficient_stock_is_rejected_and_not_decremented(client):
    h = auth(client, "greedy@example.com")
    stock = {p["id"]: p["stock"] for p in client.get("/api/products").json()}
    r = client.post("/api/orders", headers=h, json={"lines": [
        {"product_id": 2, "quantity": 1}, {"product_id": 4, "quantity": stock[4] + 1}]})
    assert r.status_code == 409
    again = {p["id"]: p["stock"] for p in client.get("/api/products").json()}
    assert again == stock


def test_admin_endpoints_are_protected(client):
    h = auth(client, "user@example.com")
    assert client.get("/api/admin/summary").status_code == 401
    assert client.get("/api/admin/summary", headers=h).status_code == 403
    assert client.get("/api/admin/orders", headers=h).status_code == 403


def test_admin_sees_sales_and_manages_products(client):
    h = auth(client, "seller@example.com")
    client.post("/api/orders", headers=h, json={"lines": [{"product_id": 3, "quantity": 1}]})
    a = admin_headers(client)
    summary = client.get("/api/admin/summary", headers=a).json()
    assert summary["orders"] >= 1 and summary["top_products"]
    orders = client.get("/api/admin/orders", headers=a).json()
    assert orders[0]["customer_email"]

    new = {"sku": "X-1", "name": "Regla", "description": "", "category": "Escritura",
           "price": "2.50", "stock": 10, "active": True}
    created = client.post("/api/admin/products", headers=a, json=new)
    assert created.status_code == 201
    assert client.post("/api/admin/products", headers=a, json=new).status_code == 409
    new["stock"] = 0
    pid = created.json()["id"]
    assert client.put(f"/api/admin/products/{pid}", headers=a, json=new).json()["stock"] == 0


def test_engine_is_internal_and_both_engines_agree(client, monkeypatch):
    from dataclasses import replace

    import api.container as container
    from api.config import settings

    h = auth(client, "versions@example.com")
    body = {"lines": [{"product_id": 2, "quantity": 2}, {"product_id": 3, "quantity": 1}]}
    totals = {}
    for engine in ("v1", "v2"):
        monkeypatch.setattr(container, "settings", replace(settings, receipt_engine=engine))
        r = client.post("/api/orders", headers=h, json=body)
        assert r.status_code == 201, r.text
        assert "engine" not in r.json() and "version" not in r.json()  # hidden from the customer
        totals[engine] = r.json()["total"]
    assert totals["v1"] == totals["v2"]
    orders = client.get("/api/admin/orders", headers=admin_headers(client)).json()
    assert {o["engine"] for o in orders[:2]} == {"v1", "v2"}  # visible to staff


def test_admin_and_client_logins_are_separate(client):
    auth(client, "plain@example.com")
    creds = {"email": "plain@example.com", "password": "password123"}
    assert client.post("/api/admin/login", json=creds).status_code == 403
    admin = {"email": "admin@test.local", "password": "admin-pass-1"}
    assert client.post("/api/auth/login", json=admin).status_code == 403
    assert client.get("/admin").status_code == 200
