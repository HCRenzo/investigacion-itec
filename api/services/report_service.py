from decimal import Decimal

from api.models import Order
from api.repositories.order import OrderRepository
from api.repositories.product import ProductRepository
from api.repositories.user import UserRepository


class ReportService:
    """Read-only figures for the admin dashboard."""

    def __init__(self, orders: OrderRepository, products: ProductRepository, users: UserRepository):
        self.orders = orders
        self.products = products
        self.users = users

    def summary(self) -> dict:
        count, revenue, units = self.orders.totals()
        return {
            "orders": count, "revenue": Decimal(revenue), "units": units,
            "customers": self.users.count_customers(),
            "top_products": [(n, int(u), Decimal(r)) for n, u, r in self.orders.top_products()],
            "low_stock": self.products.low_stock(),
            "engines": [(e, c, float(avg or 0)) for e, c, avg in self.orders.engine_stats()],
        }

    def recent_orders(self, limit: int) -> list[Order]:
        return self.orders.recent(min(max(limit, 1), 500))
