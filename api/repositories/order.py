from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.models import Order, OrderItem
from api.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    def for_user(self, user_id: int) -> list[Order]:
        return list(self.session.scalars(
            select(Order).where(Order.user_id == user_id)
            .options(selectinload(Order.items)).order_by(Order.created_at.desc())))

    def recent(self, limit: int) -> list[Order]:
        return list(self.session.scalars(
            select(Order).options(selectinload(Order.items), selectinload(Order.user))
            .order_by(Order.created_at.desc()).limit(limit)))

    def totals(self) -> tuple[int, object, int]:
        count, revenue = self.session.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))).one()
        units = self.session.scalar(select(func.coalesce(func.sum(OrderItem.quantity), 0)))
        return count, revenue, units

    def top_products(self, limit: int = 5):
        return self.session.execute(
            select(OrderItem.name, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
            .group_by(OrderItem.name).order_by(func.sum(OrderItem.quantity).desc()).limit(limit)).all()

    def engine_stats(self):
        """Orders and average processing time per receipt engine (v1 vs v2)."""
        return self.session.execute(
            select(Order.engine, func.count(Order.id), func.avg(Order.processing_seconds))
            .group_by(Order.engine).order_by(Order.engine)).all()
