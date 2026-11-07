"""Per-request wiring (dependency injection): builds repositories and services around one DB session."""
from functools import cached_property

from sqlalchemy.orm import Session

from api.config import settings
from api.repositories.order import OrderRepository
from api.repositories.product import ProductRepository
from api.repositories.user import UserRepository
from api.services.auth_service import AuthService
from api.services.catalog_service import CatalogService
from api.services.checkout_service import CheckoutService
from api.services.receipt import ReceiptEngineFactory
from api.services.report_service import ReportService
from api.services.security import PasswordHasher, TokenService


class Services:
    def __init__(self, session: Session):
        self.users = UserRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)

    @cached_property
    def auth(self) -> AuthService:
        return AuthService(self.users, PasswordHasher(), TokenService(settings))

    @cached_property
    def catalog(self) -> CatalogService:
        return CatalogService(self.products)

    @cached_property
    def checkout(self) -> CheckoutService:
        return CheckoutService(self.products, self.orders, ReceiptEngineFactory(settings))

    @cached_property
    def reports(self) -> ReportService:
        return ReportService(self.orders, self.products, self.users)
