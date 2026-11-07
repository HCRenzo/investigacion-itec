from collections.abc import Iterable

from sqlalchemy import select, update

from api.models import Product
from api.models.product import LOW_STOCK_THRESHOLD
from api.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def any_exists(self) -> bool:
        return self.session.scalar(select(Product.id).limit(1)) is not None

    def list_active(self) -> list[Product]:
        return list(self.session.scalars(
            select(Product).where(Product.active == 1).order_by(Product.category, Product.name)))

    def list_all(self) -> list[Product]:
        return list(self.session.scalars(select(Product).order_by(Product.sku)))

    def get_many_active(self, ids: Iterable[int]) -> list[Product]:
        return list(self.session.scalars(select(Product).where(Product.id.in_(list(ids)), Product.active == 1)))

    def sku_taken(self, sku: str, exclude_id: int | None = None) -> bool:
        query = select(Product.id).where(Product.sku == sku)
        if exclude_id is not None:
            query = query.where(Product.id != exclude_id)
        return self.session.scalar(query) is not None

    def low_stock(self, limit: int = 10) -> list[Product]:
        return list(self.session.scalars(
            select(Product).where(Product.active == 1, Product.stock <= LOW_STOCK_THRESHOLD)
            .order_by(Product.stock).limit(limit)))

    def reserve_stock(self, product_id: int, quantity: int) -> bool:
        """Atomic decrement. Returns False when another buyer already took the stock."""
        result = self.session.execute(
            update(Product).where(Product.id == product_id, Product.stock >= quantity)
            .values(stock=Product.stock - quantity))
        return result.rowcount == 1
