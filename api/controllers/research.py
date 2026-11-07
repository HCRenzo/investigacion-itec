"""Endpoints of the original research experiment: the same sale priced by the fast and the legacy engine."""
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from api.config import settings
from api.services.receipt import InMemoryCatalog, OrderLine, ReceiptEngineFactory
from api.views.schemas import SaleRequest

router = APIRouter(prefix="/api/sales")

PRODUCTS = {
    "P-001": {"name": "Cuaderno", "price": "12.50"},
    "P-002": {"name": "Lapicera", "price": "3.75"},
    "P-003": {"name": "Resma A4", "price": "8.90"},
    "P-004": {"name": "Mochila", "price": "29.99"},
}
_catalog = InMemoryCatalog(PRODUCTS)
_engines = ReceiptEngineFactory(settings)


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


def _summary(sale: SaleRequest, engine_name: str, prefix: str) -> SaleSummary:
    receipt = _engines.create(engine_name).calculate(
        [OrderLine(l.product_id, l.quantity) for l in sale.lines], _catalog)
    now = datetime.now(timezone.utc)
    return SaleSummary(
        receipt_number=f"{prefix}{now:%Y%m%d%H%M%S%f}", customer=sale.customer, created_at=now.isoformat(),
        items=[{"product_id": i.key, "name": i.name, "quantity": i.quantity,
                "unit_price": f"{i.unit_price:.2f}", "line_total": f"{i.line_total:.2f}"} for i in receipt.items],
        item_count=receipt.item_count, subtotal=f"{receipt.subtotal:.2f}", tax=f"{receipt.tax:.2f}",
        total=f"{receipt.total:.2f}", processing_seconds=receipt.processing_seconds)


@router.post("", response_model=SaleSummary)
def create_sale(sale: SaleRequest):
    return _summary(sale, "v2", "V-")


@router.post("/slow", response_model=SaleSummary)
def create_slow_sale(sale: SaleRequest):
    """Same sale through the deliberately inefficient legacy engine."""
    return _summary(sale, "v1", "V-LENTO-")
