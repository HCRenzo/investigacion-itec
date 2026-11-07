from decimal import Decimal

from api.config import Settings
from api.models import Product
from api.repositories.product import ProductRepository
from api.services.auth_service import AuthService

SEED_PRODUCTS = [
    ("P-001", "Cuaderno", "Cuaderno universitario de 100 hojas, tapa dura.", "Papelería", "12.50", 120),
    ("P-002", "Lapicera", "Lapicera de gel tinta negra, punta 0.7 mm.", "Escritura", "3.75", 300),
    ("P-003", "Resma A4", "Resma de 500 hojas, 75 g/m².", "Papelería", "8.90", 80),
    ("P-004", "Mochila", "Mochila resistente al agua con compartimento para laptop.", "Accesorios", "29.99", 40),
    ("P-005", "Resaltadores x4", "Set de cuatro resaltadores de colores.", "Escritura", "6.40", 150),
    ("P-006", "Calculadora científica", "Pantalla de dos líneas, 240 funciones.", "Tecnología", "18.00", 35),
]


class SeedService:
    """Creates the demo catalog and the first administrator on an empty database."""

    def __init__(self, products: ProductRepository, auth: AuthService, settings: Settings):
        self.products = products
        self.auth = auth
        self.settings = settings

    def run(self) -> None:
        if not self.products.any_exists():
            for sku, name, desc, cat, price, stock in SEED_PRODUCTS:
                self.products.add(Product(sku=sku, name=name, description=desc, category=cat,
                                          price=Decimal(price), stock=stock))
            self.products.commit()
        self.auth.ensure_admin("Administrador", self.settings.admin_email, self.settings.admin_password)
