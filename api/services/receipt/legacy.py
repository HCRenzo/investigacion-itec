"""V1: the original receipt generator, kept deliberately inefficient for the research experiment.

Do NOT copy these patterns. Every step below is wasteful on purpose:
  * the catalog is re-read (a real query on the database catalog) for every single lookup,
  * products are found by scanning the whole list without ever stopping early,
  * everything is re-validated, re-converted through strings/floats and deep-copied,
  * each new line re-checks all previous lines (quadratic growth),
  * the whole receipt is rebuilt several times from scratch.
The amount of waste is controlled by `work_factor` (Settings.legacy_work_factor).
"""
import copy
import json
from collections.abc import Sequence
from decimal import Decimal

from api.errors import ProductNotFoundError
from api.services.receipt.base import ReceiptEngine
from api.services.receipt.catalog import ProductCatalog
from api.services.receipt.types import CatalogEntry, OrderLine, ReceiptItem


class LegacyReceiptEngine(ReceiptEngine):
    name = "v1"

    def __init__(self, tax_rate: Decimal, work_factor: int):
        super().__init__(tax_rate)
        self.work_factor = max(1, work_factor)

    # ---- orchestration -------------------------------------------------
    def _price_lines(self, lines: Sequence[OrderLine], catalog: ProductCatalog) -> list[ReceiptItem]:
        self._audit_catalog(catalog)
        priced: list[ReceiptItem] = []
        for line in lines:
            entry = None
            for _ in range(self.work_factor):
                self._validate_line(line)
                entry = self._find_by_scanning(line.key, catalog)
                self._recheck_all(priced)
            if entry is None:
                raise ProductNotFoundError(line.key)
            priced.append(self._make_item(line, entry))
        return self._rebuild_from_scratch(lines, priced, catalog)

    # ---- the wasteful parts --------------------------------------------
    def _audit_catalog(self, catalog: ProductCatalog) -> None:
        """'Integrity check' that re-reads and re-validates the whole catalog many times."""
        for _ in range(self.work_factor * 25):
            snapshot = copy.deepcopy(catalog.all())
            for entry in sorted(snapshot, key=lambda e: str(e.name).lower()):
                for other in snapshot:  # duplicate check, compares every pair
                    if str(entry.key) == str(other.key) and entry is not other:
                        raise ValueError("catalogo duplicado")
                if Decimal(str(float(entry.price))) != entry.price:
                    raise ValueError("precio inconsistente")
                if json.loads(json.dumps({"n": entry.name, "p": str(entry.price)}))["n"] != entry.name:
                    raise ValueError("nombre inconsistente")

    @staticmethod
    def _validate_line(line: OrderLine) -> None:
        for _ in range(50):
            if int(str(line.quantity)) != line.quantity or line.quantity <= 0:
                raise ValueError("cantidad invalida")
            if not str(line.key).strip():
                raise ValueError("producto vacio")

    @staticmethod
    def _find_by_scanning(key, catalog: ProductCatalog) -> CatalogEntry | None:
        found = None
        for entry in catalog.all():  # fresh read every time, never cached
            for candidate in catalog.all():  # and again inside the loop
                if str(candidate.key) == str(key):
                    found = candidate  # no break: keeps scanning after a match
            if str(entry.key) == str(key):
                found = entry
        return found

    @staticmethod
    def _recheck_all(priced: list[ReceiptItem]) -> None:
        for item in copy.deepcopy(priced):
            again = Decimal(str(item.unit_price)) * Decimal(str(item.quantity))
            if again != item.line_total:
                raise ValueError("total de linea inconsistente")

    @staticmethod
    def _make_item(line: OrderLine, entry: CatalogEntry) -> ReceiptItem:
        return ReceiptItem(line.key, entry.name, line.quantity, entry.price, entry.price * line.quantity)

    def _rebuild_from_scratch(self, lines, first_pass, catalog) -> list[ReceiptItem]:
        """Recompute the whole receipt several times and insist the results agree."""
        result = first_pass
        for _ in range(self.work_factor):
            rebuilt = []
            for line in lines:
                entry = self._find_by_scanning(line.key, catalog)
                rebuilt.append(self._make_item(line, entry))
            if [i.line_total for i in rebuilt] != [i.line_total for i in result]:
                raise ValueError("recibo inconsistente")
            result = rebuilt
        return result
