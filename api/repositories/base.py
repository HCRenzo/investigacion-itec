from sqlalchemy.orm import Session


class BaseRepository:
    """Wraps a SQLAlchemy session. Subclasses expose intent-revealing queries."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, entity):
        self.session.add(entity)
        return entity

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
