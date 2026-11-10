from abc import ABC, abstractmethod
from collections.abc import Iterable
from decimal import Decimal
from typing import Hashable

from api.repositories.product import ProductRepository
from api.services.receipt.types import CatalogEntry


class ProductCatalog(ABC):
    """Read-only view of sellable products, keyed however the caller likes."""

    @abstractmethod
    def all(self) -> list[CatalogEntry]: ...

    @abstractmethod
    def find_many(self, keys: Iterable[Hashable]) -> dict[Hashable, CatalogEntry]: ...


class DatabaseCatalog(ProductCatalog):
    """Backed by the products table. Each all() call is a real query."""

    def __init__(self, products: ProductRepository):
        self.products = products

    def all(self) -> list[CatalogEntry]:
        return [CatalogEntry(p.uuid, p.name, p.price) for p in self.products.list_active()]

    def find_many(self, keys: Iterable[Hashable]) -> dict[Hashable, CatalogEntry]:
        return {p.uuid: CatalogEntry(p.uuid, p.name, p.price) for p in self.products.get_many_active(keys)}


class InMemoryCatalog(ProductCatalog):
    """Fixed catalog used by the research endpoints."""

    def __init__(self, data: dict[str, dict]):
        self._entries = {k: CatalogEntry(k, v["name"], Decimal(v["price"])) for k, v in data.items()}

    def all(self) -> list[CatalogEntry]:
        return list(self._entries.values())

    def find_many(self, keys: Iterable[Hashable]) -> dict[Hashable, CatalogEntry]:
        return {k: self._entries[k] for k in keys if k in self._entries}
