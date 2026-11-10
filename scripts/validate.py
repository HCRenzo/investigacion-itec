#!/usr/bin/env python3
"""Validates that V1 and V2 behave the same and that V2 is faster.

Needs both servers running (scripts/start_all.sh). Sends the SAME cart to each one as the demo customer
and checks: identical totals/items, the engine is hidden from the customer, staff can see which engine
priced each order, and V2 is faster. Exit code 0 = all checks passed.

    python3 scripts/validate.py [--v1 http://127.0.0.1:8011] [--v2 http://127.0.0.1:8010]
Note: it places two real orders (a few units of stock are consumed).
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

CUSTOMER = {"email": "cliente@prueba.com", "password": "cliente1234"}
ADMIN = {"email": "admin@tienda.local", "password": "admin1234"}
CART = [("P-001", 2), ("P-002", 1), ("P-003", 4)]  # sku, quantity

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, label))
    print(f"  [{'OK' if ok else 'FALLA'}] {label}" + (f"  ({detail})" if detail else ""))


def call(base: str, path: str, body=None, token=None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def buy(base: str, token: str):
    _, products = call(base, "/api/products")
    ids = {p["sku"]: p["id"] for p in products}  # public ids are uuids
    started = time.perf_counter()
    status, order = call(base, "/api/orders", {"lines": [{"product_id": ids[sku], "quantity": q} for sku, q in CART]}, token)
    return status, order, time.perf_counter() - started


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", default="http://127.0.0.1:8011")
    ap.add_argument("--v2", default="http://127.0.0.1:8010")
    args = ap.parse_args()

    print("1) Servidores disponibles")
    for name, base in (("V1", args.v1), ("V2", args.v2)):
        try:
            check(call(base, "/health", timeout=5)[0] == 200, f"{name} responde en {base}")
        except OSError as e:
            check(False, f"{name} responde en {base}", str(e))
            print("\nLevanta los servidores con scripts/start_all.sh"); return 1

    print("2) Login de cliente de prueba")
    tokens = {}
    for name, base in (("V1", args.v1), ("V2", args.v2)):
        status, data = call(base, "/api/auth/login", CUSTOMER)
        check(status == 200, f"{name}: login cliente", f"HTTP {status}")
        tokens[name] = data.get("token")
    if not all(tokens.values()):
        return 1

    print("3) Misma compra en ambas versiones (V1 tarda ~30 s, espera...)")
    orders, elapsed = {}, {}
    for name, base in (("V2", args.v2), ("V1", args.v1)):
        status, order, secs = buy(base, tokens[name])
        check(status == 201, f"{name}: compra creada", f"HTTP {status}, reloj {secs:.2f} s")
        orders[name], elapsed[name] = order, secs

    print("4) Resultados equivalentes")
    for field in ("subtotal", "tax", "total", "item_count"):
        check(orders["V1"].get(field) == orders["V2"].get(field), f"{field} igual",
              f"V1={orders['V1'].get(field)} V2={orders['V2'].get(field)}")
    strip = lambda o: [(i["name"], i["quantity"], i["unit_price"], i["line_total"]) for i in o["items"]]
    check(strip(orders["V1"]) == strip(orders["V2"]), "lineas del recibo iguales")

    print("5) El motor es interno")
    for name in ("V1", "V2"):
        leaked = {"engine", "version"} & set(orders[name])
        check(not leaked, f"{name}: la respuesta al cliente no revela el motor")

    print("6) El personal si lo ve (panel admin)")
    status, admin = call(args.v2, "/api/admin/login", ADMIN)
    check(status == 200, "login admin", f"HTTP {status}")
    if status == 200:
        _, listing = call(args.v2, "/api/admin/orders?limit=20", token=admin["token"])
        engine_of = {o["number"]: o["engine"] for o in listing}
        check(engine_of.get(orders["V1"]["number"]) == "v1", "pedido de V1 registrado como v1")
        check(engine_of.get(orders["V2"]["number"]) == "v2", "pedido de V2 registrado como v2")

    print("7) Rendimiento")
    t1, t2 = orders["V1"]["processing_seconds"], orders["V2"]["processing_seconds"]
    check(t1 > 5, "V1 es lenta (> 5 s)", f"{t1:.3f} s")
    check(t2 < 1, "V2 es rapida (< 1 s)", f"{t2:.4f} s")
    check(t1 > t2 * 100, "V2 al menos 100 veces mas rapida", f"{t1 / max(t2, 1e-9):,.0f}x")

    failed = [label for ok, label in results if not ok]
    print(f"\nResumen: V1 {t1:.2f} s | V2 {t2:.4f} s | {len(results) - len(failed)}/{len(results)} comprobaciones OK")
    if failed:
        print("FALLARON:", *failed, sep="\n  - ")
        return 1
    print("VALIDACION CORRECTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
