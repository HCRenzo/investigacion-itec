from datetime import datetime, timezone

from sqlalchemy import func, select

from api.models import ROLE_CUSTOMER, Role, User
from api.repositories.base import BaseRepository


class RoleRepository(BaseRepository):
    def by_code(self, code: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.code == code, Role.deleted_at.is_(None)))


class UserRepository(BaseRepository):
    def get(self, user_id: int) -> User | None:
        return self.session.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(func.lower(User.email) == email.lower(), User.deleted_at.is_(None)))

    def count_customers(self) -> int:
        return self.session.scalar(
            select(func.count(User.id)).join(Role, User.role_id == Role.id)
            .where(Role.code == ROLE_CUSTOMER, User.deleted_at.is_(None)))

    def touch_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        self.commit()
