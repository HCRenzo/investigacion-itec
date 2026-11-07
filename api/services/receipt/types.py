"""Plain value objects shared by the receipt engines. They know nothing about HTTP or the database."""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Hashable


@dataclass(frozen=True)
class CatalogEntry:
    key: Hashable
    name: str
    price: Decimal


@dataclass(frozen=True)
class OrderLine:
    key: Hashable
    quantity: int


@dataclass(frozen=True)
class ReceiptItem:
    key: Hashable
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


@dataclass
class Receipt:
    items: list[ReceiptItem]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    engine: str
    processing_seconds: float = 0.0
    item_count: int = field(init=False)

    def __post_init__(self):
        self.item_count = sum(i.quantity for i in self.items)
