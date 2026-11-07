from sqlalchemy import func, select

from api.models import ROLE_CUSTOMER, User
from api.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def count_customers(self) -> int:
        return self.session.scalar(select(func.count(User.id)).where(User.role == ROLE_CUSTOMER))
