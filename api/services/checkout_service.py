import uuid as uuid_lib
from datetime import datetime, timezone
from decimal import Decimal
from secrets import token_hex

from api.config import Settings
from api.errors import InsufficientStockError
from api.models import MOVEMENT_SALE, ORDER_PAID, InventoryMovement, Order, OrderItem, User
from api.repositories.order import MovementRepository, OrderRepository, ParameterRepository
from api.repositories.product import ProductRepository
from api.services.receipt import DatabaseCatalog, OrderLine, ReceiptEngineFactory

MILLIS = Decimal("0.001")


class CheckoutService:
    """Turns a cart into a persisted order. The receipt engine (v1/v2) is an internal detail."""

    def __init__(self, products: ProductRepository, orders: OrderRepository, movements: MovementRepository,
                 params: ParameterRepository, engines: ReceiptEngineFactory, settings: Settings):
        self.products = products
        self.orders = orders
        self.movements = movements
        self.params = params
        self.engines = engines
        self.settings = settings

    def checkout(self, user: User, cart: list[tuple[uuid_lib.UUID, int]]) -> Order:
        lines = self._merge(cart)
        engine = self.engines.create(self.active_engine()[0],
                                     Decimal(self.params.value("TASA_IVA") or self.settings.tax_rate))
        # Price first, touch stock afterwards: no row is locked while the engine works.
        receipt = engine.calculate(lines, DatabaseCatalog(self.products))

        products = {p.uuid: p for p in self.products.get_many_active(i.key for i in receipt.items)}
        remaining: dict[uuid_lib.UUID, int] = {}
        for item in receipt.items:
            left = self.products.reserve_stock(item.key, item.quantity)
            if left is None:
                self.products.rollback()
                raise InsufficientStockError(item.name)
            remaining[item.key] = left

        now = datetime.now(timezone.utc)
        order = Order(
            number=f"V-{now:%Y%m%d}-{token_hex(3).upper()}", user_id=user.id, user=user, created_at=now,
            status=ORDER_PAID, subtotal=receipt.subtotal, tax_rate=engine.tax_rate, tax=receipt.tax,
            total=receipt.total, engine=receipt.engine,
            processing_seconds=Decimal(str(receipt.processing_seconds)).quantize(MILLIS),
            items=[OrderItem(product_id=products[i.key].id, name=i.name, unit_price=i.unit_price,
                             quantity=i.quantity, line_total=i.line_total) for i in receipt.items])
        self.orders.add(order)
        self.orders.flush()  # assigns order.id for the stock ledger
        for item in receipt.items:
            self.movements.add(InventoryMovement(
                product_id=products[item.key].id, order_id=order.id, type=MOVEMENT_SALE,
                quantity=-item.quantity, stock_after=remaining[item.key], reason=f"Venta {order.number}"))
        self.orders.commit()
        return order

    def active_engine(self) -> tuple[str, str]:
        """(engine, where it came from): RECEIPT_ENGINE env var first, then t_parametro.MOTOR_RECIBO, then v2."""
        if self.settings.receipt_engine:
            return self.settings.receipt_engine, "variable de entorno RECEIPT_ENGINE"
        stored = self.params.value("MOTOR_RECIBO")
        if stored:
            return stored.lower(), "t_parametro (MOTOR_RECIBO)"
        return "v2", "valor por defecto"

    def history(self, user: User) -> list[Order]:
        return self.orders.for_user(user.id)

    @staticmethod
    def _merge(cart: list[tuple[uuid_lib.UUID, int]]) -> list[OrderLine]:
        wanted: dict[uuid_lib.UUID, int] = {}
        for product_uuid, quantity in cart:
            wanted[product_uuid] = wanted.get(product_uuid, 0) + quantity
        return [OrderLine(key, qty) for key, qty in wanted.items()]
