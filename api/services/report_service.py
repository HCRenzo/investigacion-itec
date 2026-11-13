from decimal import Decimal

from sqlalchemy import func, select

from api.database import describe_database
from api.models import AuditLog, InventoryMovement, Order, OrderItem, Product, User
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

    def database_status(self) -> dict:
        """Which database this deployment talks to and how many rows each table has (proves reads work)."""
        info = describe_database()
        session = self.users.session
        tables = {"t_usuario": User, "t_producto": Product, "t_pedido": Order, "t_pedido_detalle": OrderItem,
                  "t_movimiento_inventario": InventoryMovement, "t_auditoria": AuditLog}
        try:
            info["counts"] = {name: session.scalar(select(func.count(model.id))) for name, model in tables.items()}
            info["connected"] = True
        except Exception as exc:  # tables missing, bad credentials, network...
            session.rollback()
            info.update(connected=False, counts={}, error=type(exc).__name__)
        return info
