"""Base class with the standard columns every t_* table carries: id, uuid and audit fields.

The same columns are created by supabase/migrations/0001_esquema.sql. In Postgres the foreign keys
(created_by -> t_usuario ...) and the triggers live in the database; here they are plain columns so the
ORM has no ambiguous join paths. created_by / updated_by are stamped from `session.info["user_id"]`.
"""
import uuid as uuid_lib
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, Uuid, event, text
from sqlalchemy.orm import Mapped, Session, mapped_column

BigId = BigInteger().with_variant(Integer, "sqlite")  # SQLite only autoincrements INTEGER keys


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditedEntity:
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(Uuid, unique=True, default=uuid_lib.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[int | None] = mapped_column(BigId, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    updated_by: Mapped[int | None] = mapped_column(BigId, default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_by: Mapped[int | None] = mapped_column(BigId, default=None)

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()


@event.listens_for(Session, "before_flush")
def _stamp_audit_users(session: Session, flush_context, instances) -> None:
    user_id = session.info.get("user_id")
    for obj in session.new:
        if isinstance(obj, AuditedEntity):
            obj.created_by = obj.created_by if obj.created_by is not None else user_id
            obj.updated_by = obj.updated_by if obj.updated_by is not None else user_id
    if user_id is None:
        return
    for obj in session.dirty:
        if isinstance(obj, AuditedEntity) and session.is_modified(obj):
            obj.updated_by = user_id
            if obj.deleted_at is not None and obj.deleted_by is None:
                obj.deleted_by = user_id


@event.listens_for(Session, "after_begin")
def _tell_postgres_who_is_acting(session: Session, transaction, connection) -> None:
    """Lets the database triggers (t_auditoria, created_by...) know the acting user for this transaction."""
    if connection.dialect.name == "postgresql":
        user_id = session.info.get("user_id")
        connection.execute(text("select set_config('app.user_id', :u, true)"),
                           {"u": str(user_id) if user_id is not None else ""})
