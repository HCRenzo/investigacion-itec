import uuid as uuid_lib
from collections.abc import Iterable

from sqlalchemy import select, update

from api.models import Category, Product
from api.models.entities import LOW_STOCK_THRESHOLD
from api.repositories.base import BaseRepository


class CategoryRepository(BaseRepository):
    def get_or_create(self, name: str) -> Category:
        from sqlalchemy import func
        name = name.strip() or "General"
        found = self.session.scalar(
            select(Category).where(func.lower(Category.name) == name.lower(), Category.deleted_at.is_(None)))
        return found or self.add(Category(name=name))


class ProductRepository(BaseRepository):
    def _alive(self):
        return Product.deleted_at.is_(None)

    def by_uuid(self, product_uuid: uuid_lib.UUID) -> Product | None:
        return self.session.scalar(select(Product).where(Product.uuid == product_uuid, self._alive()))

    def any_exists(self) -> bool:
        return self.session.scalar(select(Product.id).where(self._alive()).limit(1)) is not None

    def list_active(self) -> list[Product]:
        return list(self.session.scalars(
            select(Product).where(Product.active.is_(True), self._alive())
            .join(Category, Product.category_id == Category.id).order_by(Category.name, Product.name)))

    def list_all(self) -> list[Product]:
        return list(self.session.scalars(select(Product).where(self._alive()).order_by(Product.sku)))

    def get_many_active(self, uuids: Iterable[uuid_lib.UUID]) -> list[Product]:
        return list(self.session.scalars(
            select(Product).where(Product.uuid.in_(list(uuids)), Product.active.is_(True), self._alive())))

    def sku_taken(self, sku: str, exclude_uuid: uuid_lib.UUID | None = None) -> bool:
        query = select(Product.id).where(Product.sku == sku, self._alive())
        if exclude_uuid is not None:
            query = query.where(Product.uuid != exclude_uuid)
        return self.session.scalar(query) is not None

    def low_stock(self, limit: int = 10) -> list[Product]:
        return list(self.session.scalars(
            select(Product).where(Product.active.is_(True), self._alive(), Product.stock <= LOW_STOCK_THRESHOLD)
            .order_by(Product.stock).limit(limit)))

    def reserve_stock(self, product_uuid: uuid_lib.UUID, quantity: int) -> int | None:
        """Atomic decrement. Returns the remaining stock, or None if another buyer already took it."""
        statement = (update(Product)
                     .where(Product.uuid == product_uuid, Product.stock >= quantity, self._alive())
                     .values(stock=Product.stock - quantity, updated_by=self.session.info.get("user_id"))
                     .returning(Product.stock)
                     .execution_options(synchronize_session=False))
        return self.session.execute(statement).scalar_one_or_none()
