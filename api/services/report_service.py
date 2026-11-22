from decimal import Decimal

from sqlalchemy import func, select

from api.database import describe_database
from api.models import AuditLog, Category, InventoryMovement, Order, OrderItem, Product, User
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

    def dataset(self, limit: int = 5000) -> dict:
        """Everything the 'Base de datos' charts need, aggregated from the real tables (no personal data)."""
        session = self.users.session
        orders = [{"number": o.number, "created_at": o.created_at.isoformat() if o.created_at else None, "engine": o.engine,
                   "seconds": float(o.processing_seconds or 0), "lines": len(o.items), "units": o.item_count,
                   "total": float(o.total)} for o in self.orders.recent(limit)]
        by_product = session.execute(
            select(Product.name, Category.name, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
            .join(Product, Product.id == OrderItem.product_id).join(Category, Category.id == Product.category_id)
            .where(OrderItem.deleted_at.is_(None)).group_by(Product.name, Category.name)).all()
        stock = session.execute(
            select(Product.name, Category.name, Product.stock, Product.price)
            .join(Category, Category.id == Product.category_id).where(Product.deleted_at.is_(None))).all()
        movements: dict[tuple[str, str], int] = {}
        for created, kind, qty in session.execute(
                select(InventoryMovement.created_at, InventoryMovement.type, InventoryMovement.quantity)
                .where(InventoryMovement.deleted_at.is_(None)).limit(50000)):
            key = (created.date().isoformat() if created else "", kind)
            movements[key] = movements.get(key, 0) + abs(int(qty))
        return {
            "orders": orders,
            "by_product": [{"product": n, "category": c, "units": int(u or 0), "revenue": float(r or 0)} for n, c, u, r in by_product],
            "stock": [{"product": n, "category": c, "stock": int(st), "price": float(pr)} for n, c, st, pr in stock],
            "movements": [{"date": d, "type": t, "units": u} for (d, t), u in sorted(movements.items())],
            "database": self.database_status(),
        }
