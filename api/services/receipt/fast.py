from collections.abc import Sequence

from api.errors import ProductNotFoundError
from api.services.receipt.base import ReceiptEngine
from api.services.receipt.catalog import ProductCatalog
from api.services.receipt.types import OrderLine, ReceiptItem


class FastReceiptEngine(ReceiptEngine):
    """V2: one catalog lookup for all lines, then a single O(n) pass with direct index access."""

    name = "v2"

    def _price_lines(self, lines: Sequence[OrderLine], catalog: ProductCatalog) -> list[ReceiptItem]:
        index = catalog.find_many({line.key for line in lines})
        items = []
        for line in lines:
            entry = index.get(line.key)
            if entry is None:
                raise ProductNotFoundError(line.key)
            items.append(ReceiptItem(line.key, entry.name, line.quantity, entry.price, entry.price * line.quantity))
        return items
