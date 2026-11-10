"""ORM entities. Python attributes keep English names used across the code base;
the columns map to the Spanish t_* schema (see docs/PLAN_BASE_DE_DATOS.md)."""
import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.audit import AuditedEntity, BigId

ROLE_ADMIN = "ADMIN"
ROLE_CUSTOMER = "CLIENTE"
LOW_STOCK_THRESHOLD = 10

ORDER_PAID = "PAGADO"
MOVEMENT_SALE, MOVEMENT_IN, MOVEMENT_ADJUST = "VENTA", "INGRESO", "AJUSTE"


class Role(AuditedEntity, Base):
    __tablename__ = "t_rol"
    code: Mapped[str] = mapped_column("codigo", String(20))
    name: Mapped[str] = mapped_column("nombre", String(60))
    description: Mapped[str] = mapped_column("descripcion", String(200), default="")


class User(AuditedEntity, Base):
    __tablename__ = "t_usuario"
    role_id: Mapped[int] = mapped_column("rol_id", ForeignKey("t_rol.id"))
    name: Mapped[str] = mapped_column("nombre", String(120))
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column("ultimo_login_at", DateTime(timezone=True), default=None)

    rol: Mapped[Role] = relationship(lazy="joined")

    @property
    def is_admin(self) -> bool:
        return self.rol.code == ROLE_ADMIN

    @property
    def role(self) -> str:
        """Role name exposed to the front end ('admin' / 'customer')."""
        return "admin" if self.is_admin else "customer"


class Category(AuditedEntity, Base):
    __tablename__ = "t_categoria"
    name: Mapped[str] = mapped_column("nombre", String(60))
    description: Mapped[str] = mapped_column("descripcion", String(200), default="")


class Product(AuditedEntity, Base):
    __tablename__ = "t_producto"
    category_id: Mapped[int] = mapped_column("categoria_id", ForeignKey("t_categoria.id"))
    sku: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column("nombre", String(160))
    description: Mapped[str] = mapped_column("descripcion", String(500), default="")
    price: Mapped[Decimal] = mapped_column("precio", Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)

    category: Mapped[Category] = relationship(lazy="joined")

    @property
    def is_active(self) -> bool:
        return bool(self.active)

    @property
    def is_low_stock(self) -> bool:
        return self.stock <= LOW_STOCK_THRESHOLD


class Order(AuditedEntity, Base):
    __tablename__ = "t_pedido"
    number: Mapped[str] = mapped_column("numero", String(40))
    user_id: Mapped[int] = mapped_column("usuario_id", ForeignKey("t_usuario.id"))
    status: Mapped[str] = mapped_column("estado", String(20), default=ORDER_PAID)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[Decimal] = mapped_column("tasa_impuesto", Numeric(5, 4))
    tax: Mapped[Decimal] = mapped_column("impuesto", Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Internal telemetry: which receipt engine produced it and how long it took.
    engine: Mapped[str] = mapped_column("motor_recibo", String(10), default="v2")
    processing_seconds: Mapped[Decimal] = mapped_column("tiempo_proceso_seg", Numeric(10, 3), default=Decimal("0"))

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")
    items: Mapped[list["OrderItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)


class OrderItem(AuditedEntity, Base):
    __tablename__ = "t_pedido_detalle"
    order_id: Mapped[int] = mapped_column("pedido_id", ForeignKey("t_pedido.id"))
    product_id: Mapped[int] = mapped_column("producto_id", ForeignKey("t_producto.id"))
    name: Mapped[str] = mapped_column("nombre_producto", String(160))
    unit_price: Mapped[Decimal] = mapped_column("precio_unitario", Numeric(12, 2))
    quantity: Mapped[int] = mapped_column("cantidad", Integer)
    line_total: Mapped[Decimal] = mapped_column("total_linea", Numeric(12, 2))


class InventoryMovement(AuditedEntity, Base):
    __tablename__ = "t_movimiento_inventario"
    product_id: Mapped[int] = mapped_column("producto_id", ForeignKey("t_producto.id"))
    order_id: Mapped[int | None] = mapped_column("pedido_id", ForeignKey("t_pedido.id"), default=None)
    type: Mapped[str] = mapped_column("tipo", String(20))
    quantity: Mapped[int] = mapped_column("cantidad", Integer)  # negative = leaves stock
    stock_after: Mapped[int] = mapped_column("stock_resultante", Integer)
    reason: Mapped[str] = mapped_column("motivo", String(200), default="")


class AuditLog(AuditedEntity, Base):
    """Filled by database triggers in Postgres; the app only reads it."""
    __tablename__ = "t_auditoria"
    table_name: Mapped[str] = mapped_column("tabla", String(60))
    record_uuid: Mapped[uuid_lib.UUID] = mapped_column("registro_uuid")
    action: Mapped[str] = mapped_column("accion", String(10))
    data_before: Mapped[dict | None] = mapped_column("datos_antes", JSON().with_variant(JSONB, "postgresql"), default=None)
    data_after: Mapped[dict | None] = mapped_column("datos_despues", JSON().with_variant(JSONB, "postgresql"), default=None)
    user_id: Mapped[int | None] = mapped_column("usuario_id", BigId, default=None)


class Parameter(AuditedEntity, Base):
    __tablename__ = "t_parametro"
    key: Mapped[str] = mapped_column("clave", String(60))
    value: Mapped[str] = mapped_column("valor", String(200))
    description: Mapped[str] = mapped_column("descripcion", String(200), default="")
