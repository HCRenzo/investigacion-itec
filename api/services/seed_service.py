from decimal import Decimal

from api.config import Settings
from api.models import MOVEMENT_IN, ROLE_ADMIN, ROLE_CUSTOMER, Product, Role
from api.repositories.order import MovementRepository, ParameterRepository
from api.repositories.product import CategoryRepository, ProductRepository
from api.repositories.user import RoleRepository
from api.services.auth_service import AuthService

ROLES = [(ROLE_ADMIN, "Administrador", "Gestiona ventas e inventario"),
         (ROLE_CUSTOMER, "Cliente", "Compra en la tienda")]

SEED_PRODUCTS = [  # sku, nombre, descripcion, categoria, precio, stock
    ("P-001", "Cuaderno", "Cuaderno universitario de 100 hojas, tapa dura.", "Papelería", "12.50", 120),
    ("P-002", "Lapicera", "Lapicera de gel tinta negra, punta 0.7 mm.", "Escritura", "3.75", 300),
    ("P-003", "Resma A4", "Resma de 500 hojas, 75 g/m².", "Papelería", "8.90", 80),
    ("P-004", "Mochila", "Mochila resistente al agua con compartimento para laptop.", "Accesorios", "29.99", 40),
    ("P-005", "Resaltadores x4", "Set de cuatro resaltadores de colores.", "Escritura", "6.40", 150),
    ("P-006", "Calculadora científica", "Pantalla de dos líneas, 240 funciones.", "Tecnología", "18.00", 35),
    ("P-007", "Carpeta archivadora A4", "Carpeta de palanca con lomo de 8 cm.", "Oficina", "5.20", 90),
    ("P-008", "Marcadores permanentes x6", "Punta redonda, colores surtidos.", "Escritura", "9.80", 110),
    ("P-009", "Notas adhesivas x5", "Bloques de 76 x 76 mm, 100 hojas cada uno.", "Papelería", "7.30", 200),
    ("P-010", "Tijeras de oficina", "Acero inoxidable, mango ergonómico.", "Oficina", "4.60", 70),
    ("P-011", "Pegamento en barra x3", "No tóxico, secado rápido.", "Papelería", "3.20", 180),
    ("P-012", "Calculadora básica", "12 dígitos, solar y pila.", "Tecnología", "9.90", 60),
    ("P-013", "Mouse inalámbrico", "Receptor USB, 1600 DPI.", "Tecnología", "14.99", 45),
    ("P-014", "Memoria USB 64 GB", "USB 3.0, carcasa metálica.", "Tecnología", "11.50", 8),
    ("P-015", "Estuche escolar", "Dos compartimentos con cierre.", "Accesorios", "6.80", 95),
    ("P-016", "Agenda 2027", "Planificador semanal, tapa blanda.", "Papelería", "15.00", 6),
    ("P-017", "Audífonos con micrófono", "Diadema ajustable, cable de 1.8 m.", "Tecnología", "22.00", 25),
    ("P-018", "Cinta adhesiva x4", "Transparente, 48 mm x 50 m.", "Oficina", "4.10", 140),
]


class SeedService:
    """Idempotent: creates roles, parameters, the demo catalog and the first users when they are missing."""

    def __init__(self, products: ProductRepository, categories: CategoryRepository, roles: RoleRepository,
                 params: ParameterRepository, movements: MovementRepository, auth: AuthService,
                 settings: Settings):
        self.products = products
        self.categories = categories
        self.roles = roles
        self.params = params
        self.movements = movements
        self.auth = auth
        self.settings = settings

    def run(self) -> None:
        for code, name, description in ROLES:
            if self.roles.by_code(code) is None:
                self.roles.add(Role(code=code, name=name, description=description))
        self.params.ensure("TASA_IVA", str(self.settings.tax_rate), "Tasa de impuesto aplicada a los pedidos")
        self.params.ensure("MOTOR_RECIBO", "v2", "Motor de calculo del recibo: v1 (lento) o v2 (rapido)")
        self.products.commit()

        if not self.products.any_exists():
            for sku, name, desc, category, price, stock in SEED_PRODUCTS:
                product = self.products.add(Product(category=self.categories.get_or_create(category), sku=sku,
                                                    name=name, description=desc, price=Decimal(price), stock=stock))
                self.products.flush()
                self.movements.record(product.id, MOVEMENT_IN, stock, stock, reason="Stock inicial")
            self.products.commit()

        self.auth.ensure_admin("Administrador", self.settings.admin_email, self.settings.admin_password)
        if self.settings.seed_demo_customer:
            self.auth.ensure_user("Cliente Prueba", self.settings.demo_customer_email,
                                  self.settings.demo_customer_password, ROLE_CUSTOMER)
