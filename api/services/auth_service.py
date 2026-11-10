from api.errors import ConflictError, ForbiddenError, UnauthorizedError
from api.models import ROLE_ADMIN, ROLE_CUSTOMER, User
from api.repositories.user import RoleRepository, UserRepository
from api.services.security import PasswordHasher, TokenService


class AuthService:
    """Registration, login and token authentication. Customers and admins log in through separate doors."""

    def __init__(self, users: UserRepository, roles: RoleRepository, hasher: PasswordHasher, tokens: TokenService):
        self.users = users
        self.roles = roles
        self.hasher = hasher
        self.tokens = tokens

    def register(self, name: str, email: str, password: str, role_code: str = ROLE_CUSTOMER) -> tuple[str, User]:
        if self.users.by_email(email):
            raise ConflictError("Ya existe una cuenta con ese correo")
        role = self.roles.by_code(role_code)
        user = self.users.add(User(name=name.strip(), email=email, rol=role, role_id=role.id,
                                   password_hash=self.hasher.hash(password)))
        self.users.commit()
        return self.tokens.issue(user.id), user

    def login_customer(self, email: str, password: str) -> tuple[str, User]:
        user = self._verified(email, password)
        if user.is_admin:
            raise ForbiddenError("Las cuentas de administrador ingresan por /admin")
        return self._start_session(user)

    def login_admin(self, email: str, password: str) -> tuple[str, User]:
        user = self._verified(email, password)
        if not user.is_admin:
            raise ForbiddenError("Esta cuenta no tiene acceso al panel de administración")
        return self._start_session(user)

    def authenticate(self, token: str) -> User:
        user = self.users.get(self.tokens.read_user_id(token))
        if user is None or not user.active:
            raise UnauthorizedError("Sesión inválida o expirada")
        self.users.act_as(user.id)  # everything written in this request is audited under this user
        return user

    def ensure_user(self, name: str, email: str, password: str, role_code: str) -> None:
        if self.users.by_email(email) is None:
            self.register(name, email, password, role_code=role_code)

    def ensure_admin(self, name: str, email: str, password: str) -> None:
        self.ensure_user(name, email, password, ROLE_ADMIN)

    def _start_session(self, user: User) -> tuple[str, User]:
        self.users.act_as(user.id)
        self.users.touch_login(user)
        return self.tokens.issue(user.id), user

    def _verified(self, email: str, password: str) -> User:
        user = self.users.by_email(email.strip().lower())
        if user is None or not user.active or not self.hasher.verify(password, user.password_hash):
            raise UnauthorizedError("Correo o contraseña incorrectos")
        return user
