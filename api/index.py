from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter, sleep

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Modulo de ventas optimizado", version="1.0.0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Catalog indexes avoid a complete catalog scan for every receipt line.
PRODUCTS = {
    "P-001": {"name": "Cuaderno", "price": Decimal("12.50")},
    "P-002": {"name": "Lapicera", "price": Decimal("3.75")},
    "P-003": {"name": "Resma A4", "price": Decimal("8.90")},
    "P-004": {"name": "Mochila", "price": Decimal("29.99")},
}


class SaleLine(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class SaleRequest(BaseModel):
    customer: str = Field(min_length=1, max_length=120)
    lines: list[SaleLine] = Field(min_length=1, max_length=500)


class SaleSummary(BaseModel):
    receipt_number: str
    customer: str
    created_at: str
    items: list[dict]
    item_count: int
    subtotal: str
    tax: str
    total: str
    processing_seconds: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/sales", response_model=SaleSummary)
def create_sale(sale: SaleRequest):
    started = perf_counter()
    receipt_items = []
    subtotal = Decimal("0")

    # Direct lookups and Decimal arithmetic keep transaction processing linear.
    for line in sale.lines:
        product = PRODUCTS.get(line.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Producto no encontrado: {line.product_id}")
        line_total = product["price"] * line.quantity
        subtotal += line_total
        receipt_items.append({
            "product_id": line.product_id,
            "name": product["name"],
            "quantity": line.quantity,
            "unit_price": f"{product['price']:.2f}",
            "line_total": f"{line_total:.2f}",
        })

    tax = (subtotal * Decimal("0.21")).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))
    elapsed = perf_counter() - started

    return SaleSummary(
        receipt_number=f"V-{datetime.now(timezone.utc):%Y%m%d%H%M%S%f}",
        customer=sale.customer,
        created_at=datetime.now(timezone.utc).isoformat(),
        items=receipt_items,
        item_count=sum(line.quantity for line in sale.lines),
        subtotal=f"{subtotal:.2f}",
        tax=f"{tax:.2f}",
        total=f"{total:.2f}",
        processing_seconds=round(elapsed, 6),
    )


@app.post("/api/sales/slow", response_model=SaleSummary)
def create_slow_sale(sale: SaleRequest):
    """Simulates the receipt problem for the research experiment."""
    started = perf_counter()

    # Deliberately redundant validation passes.
    for _ in range(20):
        normalized_customer = sale.customer.strip().upper()
        if not normalized_customer or len(normalized_customer) > 120:
            raise HTTPException(status_code=422, detail="Cliente invalido")

    receipt_items = []
    subtotal = Decimal("0")

    for line in sale.lines:
        # Intentional linear catalog scan; repeated for every validation pass.
        product = None
        for _ in range(20):
            for product_id, catalog_product in PRODUCTS.items():
                if product_id == line.product_id:
                    product = catalog_product

        if product is None:
            raise HTTPException(status_code=404, detail=f"Producto no encontrado: {line.product_id}")
        line_total = product["price"] * line.quantity
        subtotal += line_total
        receipt_items.append({
            "product_id": line.product_id,
            "name": product["name"],
            "quantity": line.quantity,
            "unit_price": f"{product['price']:.2f}",
            "line_total": f"{line_total:.2f}",
        })

    # This models the fixed 30-second delay observed in the problem scenario.
    sleep(30)

    tax = (subtotal * Decimal("0.21")).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))
    elapsed = perf_counter() - started

    return SaleSummary(
        receipt_number=f"V-LENTO-{datetime.now(timezone.utc):%Y%m%d%H%M%S%f}",
        customer=sale.customer,
        created_at=datetime.now(timezone.utc).isoformat(),
        items=receipt_items,
        item_count=sum(line.quantity for line in sale.lines),
        subtotal=f"{subtotal:.2f}",
        tax=f"{tax:.2f}",
        total=f"{total:.2f}",
        processing_seconds=round(elapsed, 3),
    )


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = PROJECT_ROOT / "static" / "index.html"
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


if (PROJECT_ROOT / "static").is_dir():
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
