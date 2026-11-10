import uuid as uuid_lib

from api.errors import ConflictError, NotFoundError
from api.models import MOVEMENT_ADJUST, MOVEMENT_IN, Product
from api.repositories.order import MovementRepository
from api.repositories.product import CategoryRepository, ProductRepository


class CatalogService:
    def __init__(self, products: ProductRepository, categories: CategoryRepository, movements: MovementRepository):
        self.products = products
        self.categories = categories
        self.movements = movements

    def storefront(self) -> list[Product]:
        return self.products.list_active()

    def inventory(self) -> list[Product]:
        return self.products.list_all()

    def create(self, data: dict) -> Product:
        if self.products.sku_taken(data["sku"]):
            raise ConflictError("Ya existe un producto con ese SKU")
        category = self.categories.get_or_create(data["category"])
        product = self.products.add(Product(
            category=category, sku=data["sku"], name=data["name"], description=data["description"],
            price=data["price"], stock=data["stock"], active=data["active"]))
        self.products.flush()
        if product.stock:
            self.movements.record(product.id, MOVEMENT_IN, product.stock, product.stock, reason="Stock inicial")
        self.products.commit()
        return product

    def update(self, product_uuid: uuid_lib.UUID, data: dict) -> Product:
        product = self.products.by_uuid(product_uuid)
        if product is None:
            raise NotFoundError("Producto no encontrado")
        if self.products.sku_taken(data["sku"], exclude_uuid=product_uuid):
            raise ConflictError("Ya existe un producto con ese SKU")
        previous_stock = product.stock
        product.category = self.categories.get_or_create(data["category"])
        for field in ("sku", "name", "description", "price", "stock", "active"):
            setattr(product, field, data[field])
        self.products.flush()
        if product.stock != previous_stock:
            self.movements.record(product.id, MOVEMENT_ADJUST, product.stock - previous_stock, product.stock,
                                  reason="Ajuste desde el panel de administración")
        self.products.commit()
        return product
