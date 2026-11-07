from api.errors import ConflictError, NotFoundError
from api.models import Product
from api.repositories.product import ProductRepository


class CatalogService:
    def __init__(self, products: ProductRepository):
        self.products = products

    def storefront(self) -> list[Product]:
        return self.products.list_active()

    def inventory(self) -> list[Product]:
        return self.products.list_all()

    def create(self, data: dict) -> Product:
        if self.products.sku_taken(data["sku"]):
            raise ConflictError("Ya existe un producto con ese SKU")
        product = self.products.add(Product(**{**data, "active": int(data["active"])}))
        self.products.commit()
        return product

    def update(self, product_id: int, data: dict) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundError("Producto no encontrado")
        if self.products.sku_taken(data["sku"], exclude_id=product_id):
            raise ConflictError("Ya existe un producto con ese SKU")
        for key, value in data.items():
            setattr(product, key, int(value) if key == "active" else value)
        self.products.commit()
        return product
