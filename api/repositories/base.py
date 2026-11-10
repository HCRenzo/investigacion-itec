from sqlalchemy.orm import Session


class BaseRepository:
    """Wraps a SQLAlchemy session. Subclasses expose intent-revealing queries.
    All reads ignore soft-deleted rows (deleted_at IS NOT NULL)."""

    def __init__(self, session: Session):
        self.session = session

    def act_as(self, user_id: int | None) -> None:
        """Records who is acting; stamped into created_by/updated_by and the audit triggers."""
        self.session.info["user_id"] = user_id

    def add(self, entity):
        self.session.add(entity)
        return entity

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
