from sqlalchemy import func, select

from api.models import InventoryMovement, Order, OrderItem, Parameter
from api.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    def for_user(self, user_id: int) -> list[Order]:
        return list(self.session.scalars(
            select(Order).where(Order.user_id == user_id, Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())))

    def recent(self, limit: int) -> list[Order]:
        return list(self.session.scalars(
            select(Order).where(Order.deleted_at.is_(None)).order_by(Order.created_at.desc()).limit(limit)))

    def totals(self) -> tuple[int, object, int]:
        count, revenue = self.session.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
            .where(Order.deleted_at.is_(None))).one()
        units = self.session.scalar(
            select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(OrderItem.deleted_at.is_(None)))
        return count, revenue, units

    def top_products(self, limit: int = 5):
        return self.session.execute(
            select(OrderItem.name, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
            .where(OrderItem.deleted_at.is_(None))
            .group_by(OrderItem.name).order_by(func.sum(OrderItem.quantity).desc()).limit(limit)).all()

    def engine_stats(self):
        """Orders and average processing time per receipt engine (v1 vs v2)."""
        return self.session.execute(
            select(Order.engine, func.count(Order.id), func.avg(Order.processing_seconds))
            .where(Order.deleted_at.is_(None)).group_by(Order.engine).order_by(Order.engine)).all()


class MovementRepository(BaseRepository):
    """Stock ledger (kardex): one row per stock change."""

    def record(self, product_id: int, kind: str, quantity: int, stock_after: int,
               order_id: int | None = None, reason: str = "") -> InventoryMovement:
        return self.add(InventoryMovement(product_id=product_id, order_id=order_id, type=kind,
                                          quantity=quantity, stock_after=stock_after, reason=reason))


class ParameterRepository(BaseRepository):
    def value(self, key: str) -> str | None:
        return self.session.scalar(
            select(Parameter.value).where(Parameter.key == key, Parameter.deleted_at.is_(None)))

    def ensure(self, key: str, value: str, description: str = "") -> None:
        if self.value(key) is None:
            self.add(Parameter(key=key, value=value, description=description))
