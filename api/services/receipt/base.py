from abc import ABC, abstractmethod
from collections.abc import Sequence
from decimal import Decimal
from time import perf_counter

from api.services.receipt.catalog import ProductCatalog
from api.services.receipt.types import OrderLine, Receipt, ReceiptItem

CENT = Decimal("0.01")


class ReceiptEngine(ABC):
    """Template method: subclasses decide HOW lines are priced, the base class totals and times it."""

    name: str

    def __init__(self, tax_rate: Decimal):
        self.tax_rate = tax_rate

    def calculate(self, lines: Sequence[OrderLine], catalog: ProductCatalog) -> Receipt:
        started = perf_counter()
        items = self._price_lines(lines, catalog)
        subtotal = sum((i.line_total for i in items), Decimal("0"))
        tax = (subtotal * self.tax_rate).quantize(CENT)
        return Receipt(items=items, subtotal=subtotal, tax=tax, total=(subtotal + tax).quantize(CENT),
                       engine=self.name, processing_seconds=round(perf_counter() - started, 6))

    @abstractmethod
    def _price_lines(self, lines: Sequence[OrderLine], catalog: ProductCatalog) -> list[ReceiptItem]: ...
