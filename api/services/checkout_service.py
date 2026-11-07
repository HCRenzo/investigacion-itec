from datetime import datetime, timezone
from secrets import token_hex

from api.errors import InsufficientStockError
from api.models import Order, OrderItem, User
from api.repositories.order import OrderRepository
from api.repositories.product import ProductRepository
from api.services.receipt import DatabaseCatalog, OrderLine, ReceiptEngineFactory


class CheckoutService:
    """Turns a cart into a persisted order. The receipt engine (v1/v2) is an internal detail."""

    def __init__(self, products: ProductRepository, orders: OrderRepository, engines: ReceiptEngineFactory):
        self.products = products
        self.orders = orders
        self.engines = engines

    def checkout(self, user: User, cart: list[tuple[int, int]]) -> Order:
        lines = self._merge(cart)
        engine = self.engines.create()
        # Price first, touch stock afterwards: no row is locked while the engine works.
        receipt = engine.calculate(lines, DatabaseCatalog(self.products))

        for item in receipt.items:
            if not self.products.reserve_stock(item.key, item.quantity):
                self.products.rollback()
                raise InsufficientStockError(item.name)

        now = datetime.now(timezone.utc)
        order = Order(
            number=f"V-{now:%Y%m%d}-{token_hex(3).upper()}", user_id=user.id, created_at=now,
            subtotal=receipt.subtotal, tax=receipt.tax, total=receipt.total,
            engine=receipt.engine, processing_seconds=receipt.processing_seconds,
            items=[OrderItem(product_id=i.key, name=i.name, unit_price=i.unit_price,
                             quantity=i.quantity, line_total=i.line_total) for i in receipt.items])
        self.orders.add(order)
        self.orders.commit()
        order.user = user
        return order

    def history(self, user: User) -> list[Order]:
        return self.orders.for_user(user.id)

    @staticmethod
    def _merge(cart: list[tuple[int, int]]) -> list[OrderLine]:
        wanted: dict[int, int] = {}
        for product_id, quantity in cart:
            wanted[product_id] = wanted.get(product_id, 0) + quantity
        return [OrderLine(pid, qty) for pid, qty in wanted.items()]
