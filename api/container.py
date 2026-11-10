"""Per-request wiring (dependency injection): builds repositories and services around one DB session."""
from functools import cached_property

from sqlalchemy.orm import Session

from api.config import settings
from api.models import User
from api.repositories.order import MovementRepository, OrderRepository, ParameterRepository
from api.repositories.product import CategoryRepository, ProductRepository
from api.repositories.user import RoleRepository, UserRepository
from api.services.auth_service import AuthService
from api.services.catalog_service import CatalogService
from api.services.checkout_service import CheckoutService
from api.services.receipt import ReceiptEngineFactory
from api.services.report_service import ReportService
from api.services.security import PasswordHasher, TokenService
from api.services.seed_service import SeedService


class Services:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)
        self.orders = OrderRepository(session)
        self.movements = MovementRepository(session)
        self.params = ParameterRepository(session)

    @cached_property
    def auth(self) -> AuthService:
        return AuthService(self.users, self.roles, PasswordHasher(), TokenService(settings))

    @cached_property
    def catalog(self) -> CatalogService:
        return CatalogService(self.products, self.categories, self.movements)

    @cached_property
    def checkout(self) -> CheckoutService:
        return CheckoutService(self.products, self.orders, self.movements, self.params,
                               ReceiptEngineFactory(settings), settings)

    @cached_property
    def reports(self) -> ReportService:
        return ReportService(self.orders, self.products, self.users)

    @cached_property
    def seed(self) -> SeedService:
        return SeedService(self.products, self.categories, self.roles, self.params, self.movements, self.auth,
                           settings)
