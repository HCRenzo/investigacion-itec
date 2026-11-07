from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.container import Services
from api.database import get_db
from api.errors import ForbiddenError, UnauthorizedError
from api.models import User

_bearer = HTTPBearer(auto_error=False)


def get_services(db: Session = Depends(get_db)) -> Services:
    return Services(db)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    services: Services = Depends(get_services),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Inicia sesión para continuar")
    return services.auth.authenticate(credentials.credentials)


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise ForbiddenError("Se requiere rol de administrador")
    return user
