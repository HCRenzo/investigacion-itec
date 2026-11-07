from api.errors import ConflictError, ForbiddenError, UnauthorizedError
from api.models import ROLE_ADMIN, ROLE_CUSTOMER, User
from api.repositories.user import UserRepository
from api.services.security import PasswordHasher, TokenService


class AuthService:
    """Registration, login and token authentication. Customers and admins log in through separate doors."""

    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService):
        self.users = users
        self.hasher = hasher
        self.tokens = tokens

    def register(self, name: str, email: str, password: str, role: str = ROLE_CUSTOMER) -> tuple[str, User]:
        if self.users.by_email(email):
            raise ConflictError("Ya existe una cuenta con ese correo")
        user = self.users.add(User(name=name.strip(), email=email, role=role,
                                   password_hash=self.hasher.hash(password)))
        self.users.commit()
        return self.tokens.issue(user.id), user

    def login_customer(self, email: str, password: str) -> tuple[str, User]:
        user = self._verified(email, password)
        if user.is_admin:
            raise ForbiddenError("Las cuentas de administrador ingresan por /admin")
        return self.tokens.issue(user.id), user

    def login_admin(self, email: str, password: str) -> tuple[str, User]:
        user = self._verified(email, password)
        if not user.is_admin:
            raise ForbiddenError("Esta cuenta no tiene acceso al panel de administración")
        return self.tokens.issue(user.id), user

    def authenticate(self, token: str) -> User:
        user = self.users.get(self.tokens.read_user_id(token))
        if user is None:
            raise UnauthorizedError("Sesión inválida o expirada")
        return user

    def ensure_admin(self, name: str, email: str, password: str) -> None:
        if self.users.by_email(email) is None:
            self.register(name, email, password, role=ROLE_ADMIN)

    def _verified(self, email: str, password: str) -> User:
        user = self.users.by_email(email.strip().lower())
        if user is None or not self.hasher.verify(password, user.password_hash):
            raise UnauthorizedError("Correo o contraseña incorrectos")
        return user
