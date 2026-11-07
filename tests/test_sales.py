from api.index import app
from fastapi.testclient import TestClient
from time import perf_counter

client = TestClient(app)


def sale_payload(lines=500):
    return {
        "customer": "Cliente de prueba",
        "lines": [
            {"product_id": "P-001", "quantity": 1}
            for _ in range(lines)
        ],
    }


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sale_receipt_calculation():
    response = client.post("/api/sales", json={
        "customer": "Ana Perez",
        "lines": [
            {"product_id": "P-001", "quantity": 2},
            {"product_id": "P-002", "quantity": 3},
        ],
    })

    assert response.status_code == 200
    receipt = response.json()
    assert receipt["subtotal"] == "36.25"
    assert receipt["tax"] == "7.61"
    assert receipt["total"] == "43.86"
    assert receipt["item_count"] == 5


def test_500_line_receipt_meets_research_target():
    started = perf_counter()
    response = client.post("/api/sales", json=sale_payload())
    elapsed = perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 20


def test_slow_sale_gives_same_result_as_fast_engine():
    payload = sale_payload(3)
    slow = client.post("/api/sales/slow", json=payload)
    fast = client.post("/api/sales", json=payload)

    assert slow.status_code == 200
    assert slow.json()["receipt_number"].startswith("V-LENTO-")
    for field in ("subtotal", "tax", "total", "item_count", "items"):
        assert slow.json()[field] == fast.json()[field]


def test_unknown_product_returns_clear_error():
    response = client.post("/api/sales", json={
        "customer": "Ana Perez",
        "lines": [{"product_id": "NO-EXISTE", "quantity": 1}],
    })
    assert response.status_code == 404
    assert "Producto no encontrado" in response.json()["detail"]
